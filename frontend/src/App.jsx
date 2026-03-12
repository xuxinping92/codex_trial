import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function requestJson(url, options = {}) {
  const res = await fetch(url, options)
  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const detail = data?.detail
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join(', '))
    }
    throw new Error(detail || `Request failed (${res.status})`)
  }

  return data
}

function App() {
  const [auth, setAuth] = useState({ username: '', password: '' })
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [me, setMe] = useState(null)
  const [friends, setFriends] = useState([])
  const [groups, setGroups] = useState([])
  const [messages, setMessages] = useState([])
  const [activePrivate, setActivePrivate] = useState(null)
  const [activeGroup, setActiveGroup] = useState(null)
  const [text, setText] = useState('')
  const [friendUsername, setFriendUsername] = useState('')
  const [groupName, setGroupName] = useState('')
  const [selectedMembers, setSelectedMembers] = useState([])
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token])

  useEffect(() => {
    if (!token) return
    requestJson(`${API_BASE}/me`, { headers })
      .then(setMe)
      .catch((err) => {
        setAuthError(err.message)
        localStorage.removeItem('token')
        setToken('')
      })
  }, [token, headers])

  useEffect(() => {
    if (!token || !me) return

    refreshSideData().catch(() => null)

    const wsUrl = API_BASE.replace('http', 'ws')
    const ws = new WebSocket(`${wsUrl}/ws/${me.id}`)
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.message) {
        setMessages((prev) => [...prev, payload.message])
      }
    }
    return () => ws.close()
  }, [token, me])

  const refreshSideData = async () => {
    const [friendsData, groupsData] = await Promise.all([
      requestJson(`${API_BASE}/friends`, { headers }),
      requestJson(`${API_BASE}/groups`, { headers })
    ])
    setFriends(friendsData)
    setGroups(groupsData)
  }

  const login = async () => {
    if (!auth.username || !auth.password) {
      setAuthError('请输入用户名和密码。')
      return
    }

    setAuthLoading(true)
    setAuthError('')
    try {
      const body = new URLSearchParams()
      body.append('username', auth.username)
      body.append('password', auth.password)
      const data = await requestJson(`${API_BASE}/auth/login`, { method: 'POST', body })
      localStorage.setItem('token', data.access_token)
      setToken(data.access_token)
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
  }

  const register = async () => {
    if (!auth.username || !auth.password) {
      setAuthError('请输入用户名和密码。')
      return
    }

    setAuthLoading(true)
    setAuthError('')
    try {
      await requestJson(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(auth)
      })
      await login()
    } catch (err) {
      setAuthError(err.message)
      setAuthLoading(false)
    }
  }

  const addFriend = async () => {
    const data = await requestJson(`${API_BASE}/friends/add`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ friend_username: friendUsername })
    })
    setFriends(data)
    setFriendUsername('')
  }

  const createGroup = async () => {
    await requestJson(`${API_BASE}/groups`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: groupName, member_ids: selectedMembers.map(Number) })
    })
    setGroupName('')
    setSelectedMembers([])
    await refreshSideData()
  }

  const loadPrivateHistory = async (friendId) => {
    setActiveGroup(null)
    setActivePrivate(friendId)
    setMessages(await requestJson(`${API_BASE}/messages/private/${friendId}`, { headers }))
  }

  const loadGroupHistory = async (groupId) => {
    setActivePrivate(null)
    setActiveGroup(groupId)
    setMessages(await requestJson(`${API_BASE}/messages/group/${groupId}`, { headers }))
  }

  const uploadImage = async (file) => {
    const form = new FormData()
    form.append('file', file)
    const data = await requestJson(`${API_BASE}/upload`, {
      method: 'POST',
      headers,
      body: form
    })
    return data.image_url
  }

  const sendMessage = async (imageFile = null) => {
    const imageUrl = imageFile ? await uploadImage(imageFile) : null
    const payload = { content: text, image_url: imageUrl }

    if (activePrivate) {
      await requestJson(`${API_BASE}/messages/private`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, receiver_id: activePrivate })
      })
    }

    if (activeGroup) {
      await requestJson(`${API_BASE}/messages/group`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, group_id: activeGroup })
      })
    }

    setText('')
  }

  if (!token) {
    return (
      <div className="auth">
        <h1>Mini WeChat</h1>
        <input placeholder="username" value={auth.username} onChange={(e) => setAuth({ ...auth, username: e.target.value })} />
        <input type="password" placeholder="password" value={auth.password} onChange={(e) => setAuth({ ...auth, password: e.target.value })} />
        <div className="row">
          <button onClick={login} disabled={authLoading}>{authLoading ? 'Loading...' : 'Login'}</button>
          <button onClick={register} disabled={authLoading}>{authLoading ? 'Loading...' : 'Register'}</button>
        </div>
        {authError && <p className="error-text">{authError}</p>}
      </div>
    )
  }

  return (
    <div className="layout">
      <aside>
        <h3>{me?.username}</h3>

        <section>
          <h4>Friends</h4>
          <div className="row">
            <input placeholder="friend username" value={friendUsername} onChange={(e) => setFriendUsername(e.target.value)} />
            <button onClick={addFriend}>Add</button>
          </div>
          {friends.map((f) => (
            <button key={f.id} className="list-item" onClick={() => loadPrivateHistory(f.id)}>
              {f.username}
            </button>
          ))}
        </section>

        <section>
          <h4>Groups</h4>
          <input placeholder="group name" value={groupName} onChange={(e) => setGroupName(e.target.value)} />
          <small>Select members:</small>
          {friends.map((f) => (
            <label key={f.id}>
              <input
                type="checkbox"
                checked={selectedMembers.includes(f.id)}
                onChange={(e) => {
                  if (e.target.checked) setSelectedMembers((prev) => [...prev, f.id])
                  else setSelectedMembers((prev) => prev.filter((id) => id !== f.id))
                }}
              />
              {f.username}
            </label>
          ))}
          <button onClick={createGroup}>Create Group</button>
          {groups.map((g) => (
            <button key={g.id} className="list-item" onClick={() => loadGroupHistory(g.id)}>
              #{g.name}
            </button>
          ))}
        </section>
      </aside>

      <main>
        <div className="chat-window">
          {messages.map((m) => (
            <div key={m.id} className="bubble">
              <strong>{m.sender_id}</strong>: {m.content}
              {m.image_url && <img src={`${API_BASE}${m.image_url}`} alt="chat" />}
            </div>
          ))}
        </div>

        <div className="composer">
          <input value={text} placeholder="Type message" onChange={(e) => setText(e.target.value)} />
          <input type="file" accept="image/*" onChange={(e) => e.target.files[0] && sendMessage(e.target.files[0])} />
          <button onClick={() => sendMessage()}>Send</button>
        </div>
      </main>
    </div>
  )
}

export default App
