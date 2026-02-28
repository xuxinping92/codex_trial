#!/usr/bin/env python3
"""双人中国象棋（命令行版）。

输入格式：
1) 起点 终点，例如：`b0 b2`
2) 或者四位坐标，例如：`b0b2`

坐标说明：
- 列：a-i（从红方左到右）
- 行：0-9（0 在黑方底线，9 在红方底线）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

Coord = Tuple[int, int]  # (row, col)


@dataclass(frozen=True)
class Piece:
    side: str  # 'R' or 'B'
    kind: str  # K/A/E/H/R/C/P

    def symbol(self) -> str:
        symbols = {
            ("R", "K"): "帅",
            ("R", "A"): "仕",
            ("R", "E"): "相",
            ("R", "H"): "马",
            ("R", "R"): "车",
            ("R", "C"): "炮",
            ("R", "P"): "兵",
            ("B", "K"): "将",
            ("B", "A"): "士",
            ("B", "E"): "象",
            ("B", "H"): "馬",
            ("B", "R"): "車",
            ("B", "C"): "砲",
            ("B", "P"): "卒",
        }
        return symbols[(self.side, self.kind)]


class XiangqiGame:
    def __init__(self) -> None:
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(9)] for _ in range(10)]
        self.turn = "R"
        self._setup_board()

    def _setup_board(self) -> None:
        # 黑方（上方，row=0）
        self.board[0] = [
            Piece("B", "R"),
            Piece("B", "H"),
            Piece("B", "E"),
            Piece("B", "A"),
            Piece("B", "K"),
            Piece("B", "A"),
            Piece("B", "E"),
            Piece("B", "H"),
            Piece("B", "R"),
        ]
        self.board[2][1] = Piece("B", "C")
        self.board[2][7] = Piece("B", "C")
        for c in (0, 2, 4, 6, 8):
            self.board[3][c] = Piece("B", "P")

        # 红方（下方，row=9）
        self.board[9] = [
            Piece("R", "R"),
            Piece("R", "H"),
            Piece("R", "E"),
            Piece("R", "A"),
            Piece("R", "K"),
            Piece("R", "A"),
            Piece("R", "E"),
            Piece("R", "H"),
            Piece("R", "R"),
        ]
        self.board[7][1] = Piece("R", "C")
        self.board[7][7] = Piece("R", "C")
        for c in (0, 2, 4, 6, 8):
            self.board[6][c] = Piece("R", "P")

    def print_board(self) -> None:
        print("\n    a  b  c  d  e  f  g  h  i")
        print("   " + "-" * 28)
        for r in range(10):
            row_text = []
            for c in range(9):
                p = self.board[r][c]
                row_text.append(p.symbol() if p else "·")
            print(f" {r} | " + " ".join(row_text))
            if r == 4:
                print("   | --------- 楚河汉界 ---------")
        print("\n轮到：" + ("红方" if self.turn == "R" else "黑方"))

    @staticmethod
    def in_bounds(pos: Coord) -> bool:
        r, c = pos
        return 0 <= r < 10 and 0 <= c < 9

    def in_palace(self, side: str, pos: Coord) -> bool:
        r, c = pos
        if side == "R":
            return 7 <= r <= 9 and 3 <= c <= 5
        return 0 <= r <= 2 and 3 <= c <= 5

    def crossed_river(self, side: str, row: int) -> bool:
        return row <= 4 if side == "R" else row >= 5

    def parse_move(self, text: str) -> Optional[Tuple[Coord, Coord]]:
        t = text.strip().lower().replace(" ", "")
        if len(t) != 4:
            return None
        sc, sr, dc, dr = t[0], t[1], t[2], t[3]
        if sc < "a" or sc > "i" or dc < "a" or dc > "i":
            return None
        if not sr.isdigit() or not dr.isdigit():
            return None
        src = (int(sr), ord(sc) - ord("a"))
        dst = (int(dr), ord(dc) - ord("a"))
        if self.in_bounds(src) and self.in_bounds(dst):
            return src, dst
        return None

    def piece_at(self, pos: Coord) -> Optional[Piece]:
        r, c = pos
        return self.board[r][c]

    def _line_clear_count(self, src: Coord, dst: Coord) -> int:
        sr, sc = src
        dr, dc = dst
        count = 0
        if sr == dr:
            step = 1 if dc > sc else -1
            for c in range(sc + step, dc, step):
                if self.board[sr][c] is not None:
                    count += 1
        elif sc == dc:
            step = 1 if dr > sr else -1
            for r in range(sr + step, dr, step):
                if self.board[r][sc] is not None:
                    count += 1
        return count

    def _raw_legal(self, src: Coord, dst: Coord) -> bool:
        if src == dst:
            return False
        sp = self.piece_at(src)
        dp = self.piece_at(dst)
        if sp is None:
            return False
        if dp is not None and dp.side == sp.side:
            return False

        sr, sc = src
        dr, dc = dst
        drw, dcl = dr - sr, dc - sc

        if sp.kind == "R":  # 车
            if sr != dr and sc != dc:
                return False
            return self._line_clear_count(src, dst) == 0

        if sp.kind == "C":  # 炮
            if sr != dr and sc != dc:
                return False
            blockers = self._line_clear_count(src, dst)
            if dp is None:
                return blockers == 0
            return blockers == 1

        if sp.kind == "H":  # 马
            if sorted([abs(drw), abs(dcl)]) != [1, 2]:
                return False
            if abs(drw) == 2:
                leg = (sr + drw // 2, sc)
            else:
                leg = (sr, sc + dcl // 2)
            return self.piece_at(leg) is None

        if sp.kind == "E":  # 象/相
            if abs(drw) != 2 or abs(dcl) != 2:
                return False
            eye = (sr + drw // 2, sc + dcl // 2)
            if self.piece_at(eye) is not None:
                return False
            if sp.side == "R" and dr < 5:
                return False
            if sp.side == "B" and dr > 4:
                return False
            return True

        if sp.kind == "A":  # 士/仕
            if abs(drw) != 1 or abs(dcl) != 1:
                return False
            return self.in_palace(sp.side, dst)

        if sp.kind == "K":  # 将/帅
            # 王见王
            if sc == dc and dp is not None and dp.kind == "K" and dp.side != sp.side:
                return self._line_clear_count(src, dst) == 0
            if abs(drw) + abs(dcl) != 1:
                return False
            return self.in_palace(sp.side, dst)

        if sp.kind == "P":  # 兵/卒
            forward = -1 if sp.side == "R" else 1
            if drw == forward and dcl == 0:
                return True
            if self.crossed_river(sp.side, sr) and drw == 0 and abs(dcl) == 1:
                return True
            return False

        return False

    def _find_king(self, side: str) -> Optional[Coord]:
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p and p.side == side and p.kind == "K":
                    return (r, c)
        return None

    def _kings_face(self) -> bool:
        rk = self._find_king("R")
        bk = self._find_king("B")
        if not rk or not bk:
            return False
        if rk[1] != bk[1]:
            return False
        return self._line_clear_count(rk, bk) == 0

    def in_check(self, side: str) -> bool:
        king = self._find_king(side)
        if king is None:
            return True
        enemy = "B" if side == "R" else "R"
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p and p.side == enemy and self._raw_legal((r, c), king):
                    return True
        return self._kings_face()

    def legal_move(self, src: Coord, dst: Coord) -> bool:
        sp = self.piece_at(src)
        if sp is None or sp.side != self.turn:
            return False
        if not self._raw_legal(src, dst):
            return False
        # 模拟走子后不能自陷将军
        captured = self.piece_at(dst)
        self.board[dst[0]][dst[1]] = sp
        self.board[src[0]][src[1]] = None
        bad = self.in_check(sp.side)
        self.board[src[0]][src[1]] = sp
        self.board[dst[0]][dst[1]] = captured
        return not bad

    def has_any_legal_move(self, side: str) -> bool:
        old_turn = self.turn
        self.turn = side
        try:
            for sr in range(10):
                for sc in range(9):
                    p = self.board[sr][sc]
                    if p and p.side == side:
                        for dr in range(10):
                            for dc in range(9):
                                if self.legal_move((sr, sc), (dr, dc)):
                                    return True
            return False
        finally:
            self.turn = old_turn

    def move(self, src: Coord, dst: Coord) -> Tuple[bool, str]:
        if not self.legal_move(src, dst):
            return False, "非法走法，请重试。"

        sp = self.piece_at(src)
        dp = self.piece_at(dst)
        assert sp is not None
        self.board[dst[0]][dst[1]] = sp
        self.board[src[0]][src[1]] = None

        enemy = "B" if sp.side == "R" else "R"

        if dp is not None and dp.kind == "K":
            return True, f"{'红方' if sp.side == 'R' else '黑方'}吃将，胜利！"

        self.turn = enemy

        if self.in_check(enemy):
            if not self.has_any_legal_move(enemy):
                return True, f"将死！{'红方' if sp.side == 'R' else '黑方'}获胜！"
            return True, "将军！"

        if not self.has_any_legal_move(enemy):
            return True, "无子可走，和棋。"

        return True, "走子成功。"


def main() -> None:
    game = XiangqiGame()
    print("欢迎来到中国象棋（双人命令行版）")
    print("输入示例：b0 b2 或 b0b2；输入 q 退出。")

    while True:
        game.print_board()
        text = input("请输入走法: ").strip()
        if text.lower() in {"q", "quit", "exit"}:
            print("已退出游戏。")
            break

        mv = game.parse_move(text)
        if mv is None:
            print("输入格式错误，请使用如 b0 b2 或 b0b2。")
            continue

        ok, message = game.move(*mv)
        print(message)
        if "胜" in message or "将死" in message:
            game.print_board()
            break


if __name__ == "__main__":
    main()
