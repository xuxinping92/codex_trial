import { useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8000'

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

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token])

  useEffect(() => {
    if (!token) return
    fetch(`${API_BASE}/me`, { headers })
      .then((r) => r.json())
      .then(setMe)
  }, [token, headers])

  useEffect(() => {
    if (!token || !me) return
    refreshSideData()

    const ws = new WebSocket(`ws://localhost:8000/ws/${me.id}`)
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.message) {
        setMessages((prev) => [...prev, payload.message])
      }
    }
    return () => ws.close()
  }, [token, me])

  const refreshSideData = async () => {
    const [fRes, gRes] = await Promise.all([
      fetch(`${API_BASE}/friends`, { headers }),
      fetch(`${API_BASE}/groups`, { headers })
    ])
    setFriends(await fRes.json())
    setGroups(await gRes.json())
  }

  const register = async () => {
    await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(auth)
    })
    await login()
  }

  const login = async () => {
    const body = new URLSearchParams()
    body.append('username', auth.username)
    body.append('password', auth.password)
    const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body })
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
  }

  const addFriend = async () => {
    const res = await fetch(`${API_BASE}/friends/add`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ friend_username: friendUsername })
    })
    setFriends(await res.json())
    setFriendUsername('')
  }

  const createGroup = async () => {
    await fetch(`${API_BASE}/groups`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: groupName, member_ids: selectedMembers.map(Number) })
    })
    setGroupName('')
    setSelectedMembers([])
    refreshSideData()
  }

  const loadPrivateHistory = async (friendId) => {
    setActiveGroup(null)
    setActivePrivate(friendId)
    const res = await fetch(`${API_BASE}/messages/private/${friendId}`, { headers })
    setMessages(await res.json())
  }

  const loadGroupHistory = async (groupId) => {
    setActivePrivate(null)
    setActiveGroup(groupId)
    const res = await fetch(`${API_BASE}/messages/group/${groupId}`, { headers })
    setMessages(await res.json())
  }

  const uploadImage = async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      headers,
      body: form
    })
    return (await res.json()).image_url
  }

  const sendMessage = async (imageFile = null) => {
    const image_url = imageFile ? await uploadImage(imageFile) : null
    const payload = { content: text, image_url }
    if (activePrivate) {
      payload.receiver_id = activePrivate
      await fetch(`${API_BASE}/messages/private`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
    }
    if (activeGroup) {
      payload.group_id = activeGroup
      await fetch(`${API_BASE}/messages/group`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
          <button onClick={login}>Login</button>
          <button onClick={register}>Register</button>
        </div>
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
