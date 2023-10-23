from enum import Enum
from itertools import batched, zip_longest
from typing import Self, Sequence


class Player(Enum):
    BLACK = -1
    EMPTY = +0
    WHITE = +1

    def __str__(self) -> str:
        return self.name.lower().capitalize()

    def __invert__(self) -> Self:
        if self is Player.EMPTY:
            raise ValueError("Cannot invert empty")
        else:
            return Player(-self.value)

    @property
    def home_squares(self) -> tuple:
        if self is Player.BLACK:
            return (H8, H7, G8, G7)
        if self is Player.WHITE:
            return (A1, A2, B1, B2)
        raise ValueError


class Piece:
    def __init__(self, player: Player | int) -> None:
        if isinstance(player, int):
            player = Player(player)
        self.player = player

    def __invert__(self) -> Self:
        return Piece(~self.player)

    def __str__(self) -> str:
        match self.player.value:
            case Player.BLACK.value:
                return "●"
            case Player.EMPTY.value:
                return "·"
            case Player.WHITE.value:
                return "○"
            case _:
                raise ValueError(
                    "I thought this state was unreachable "
                    f"(value was {self.player.value})."
                )

    def __repr__(self) -> str:
        return f"Piece({self.player})"

    @property
    def is_empty(self) -> bool:
        return self.player is Player.EMPTY


_P = Piece


class _Line:
    char_set: str = ""

    def __init__(self, value: int) -> None:
        if not (1 <= value <= 8):
            raise ValueError
        self.value = value

    def __str__(self) -> str:
        return self.char_set[self.value - 1]


class Rank(_Line):
    char_set: str = "12345678"


class File(_Line):
    char_set: str = "abcdefgh"


class Square:
    def __init__(self, file: int, rank: int) -> None:
        self.file: int = file
        self.rank: int = rank

    def __str__(self) -> str:
        return f"{File(self.file)}{Rank(self.rank)}"

    def __add__(self, other: Self | tuple[int, int]) -> Self:
        if isinstance(other, Square):
            file, rank = other.file, other.rank
        elif isinstance(other, tuple):
            file, rank = other
        else:
            raise TypeError()
        return Square(self.file + file, self.rank + rank)

    def __floordiv__(self, n: int) -> Self:
        if isinstance(n, int):
            return Square(self.file // n, self.rank // n)
        else:
            raise TypeError("A Square can only be divided by an int.")

    __truediv__ = __floordiv__


class Move:
    neighbors = (
        # fmt: off
        (-1, -1),
        (-1,  0),
        (-1, +1),
        ( 0, +1),
        (+1, +1),
        (+1,  0),
        (+1, -1),
        ( 0, -1),
        # fmt: on
    )

    def __init__(
        self,
        origin: Square | None = None,
        target: Square | None = None,
    ) -> None:
        self.origin = origin
        self.target = target

        if not (target is None or origin is None):
            self.center = (origin + target) / 2
        else:
            self.center = None

    def __str__(self) -> str:
        return f"{self.origin or '+'}{self.target or ''}"


class Position:
    # fmt: off
    START_BOARD = [
    #      a       b       c       d       e       f       g       h
        _P( 0), _P( 0), _P( 0), _P( 0), _P(-1), _P(-1), _P(-1), _P(-1),  # 8
        _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P(-1), _P(-1), _P(-1),  # 7
        _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P(-1), _P(-1),  # 6
        _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P(-1),  # 5
        _P(+1), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0),  # 4
        _P(+1), _P(+1), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0),  # 3
        _P(+1), _P(+1), _P(+1), _P( 0), _P( 0), _P( 0), _P( 0), _P( 0),  # 2
        _P(+1), _P(+1), _P(+1), _P(+1), _P( 0), _P( 0), _P( 0), _P( 0),  # 1
    ]

    PIECE_WEIGHTS = [
    #   a    b    c    d    e    f    g    h
        1,   1,   1,   1,   1,   2,   4,   4,  # 8
        1,   1,   1,   2,   2,   4,   4,   4,  # 7
        1,   1,   2,   5,   5,   4,   4,   2,  # 6
        1,   2,   5,  10,  10,   5,   2,   1,  # 5
        1,   2,   5,  10,  10,   5,   2,   1,  # 4
        2,   4,   2,   5,   5,   2,   1,   1,  # 3
        4,   4,   4,   2,   2,   1,   1,   1,  # 2
        4,   4,   2,   1,   1,   1,   1,   1,  # 1
    ]
    # fmt: on

    def __init__(
        self,
        board: list[Piece] = START_BOARD,
        ply: int = 0,
        last_move: Move | None = None,
    ) -> None:
        self.board = board
        self.ply = ply
        self.last_move = last_move

    def __str__(self) -> str:
        extras = (
            f"{self.to_move} to move",
            f"Move: {self.whole_move} (ply {self.ply})",
            f"Last move: {self.last_move}",
            f"Win progress: {self.win_progress}",
            f"Static evaluation: {self.static_evaluation}",
        )

        sep = "  │  "

        return f"   {' '.join(File.char_set)}{sep}\n" + "\n".join(
            f"{Rank.char_set[7 - int(i)]}  "
            + " ".join(str(c) for c in row)
            + sep
            + extra
            for (i, row), extra in zip_longest(
                enumerate(batched(self.board, n=8)), extras, fillvalue=""
            )
        )

    def __getitem__(
        self,
        square: Square,
    ):
        return self.board[square.file - (8 * square.rank) + 63]

    def __setitem__(self, square: Square, new_piece: Piece):
        board = self.board
        board[square.file - (8 * square.rank) + 63] = new_piece
        return Position(board)

    @property
    def to_move(self):
        if self.ply % 2 == 0:
            return Player.WHITE
        return Player.BLACK

    def copy(self) -> Self:
        return type(self)(self.board, self.ply, self.last_move)

    def move(self, move: Move) -> Self:
        new_pos = self.copy()
        home = self.to_move.home_squares

        # move is a placement
        if move.target is None and move.origin is None:
            if all(not self[square].is_empty for square in home):
                raise ValueError("At least one home square must be empty")
            for helper in home:
                if self[helper].is_empty:
                    self[helper] = Piece(self.to_move)

        # move is a jump
        if not (move.origin is None or move.center is None or move.target is None):
            origin_piece = self[move.origin]
            center_piece = self[move.center]
            target_piece = self[move.target]

            # values can be -1 (black), +1 (white), or +0 (empty), so comparing their
            #    difference with 0 guarantees the move follows the rules
            if (
                not origin_piece.player.value - center_piece.player.value
                == target_piece.player.value
                == 0
            ):
                raise ValueError(
                    f"Origin (was {origin_piece}) and center (was {center_piece}) "
                    "must be the same player's piece, "
                    f"and target (was {target_piece}) must be empty"
                )

            # fill the target
            new_pos[move.target] = new_pos[move.origin]

            # empty the origin
            new_pos[move.origin] = Piece(Player.EMPTY)

            # do suffocations
            for helper in (move.target + delta for delta in Move.neighbors):
                pass

            # do conversions
            for helper in (move.target + (x * 2, y * 2) for (x, y) in Move.neighbors):
                try:
                    avg: Square = (helper + move.target) / 2
                    if (
                        not self[avg].is_empty
                        and ~self[avg].player == self[helper].player
                    ):
                        new_pos[avg] = Piece(self.to_move)
                except IndexError:
                    pass

        new_pos.ply += 1
        new_pos.last_move = move

        return new_pos

    @property
    def win_progress(self) -> int:
        win_squares = (D4, E4, D5, E5)
        return sum(self[square].player.value for square in win_squares)

    @property
    def winner(self) -> Player:
        _signum = lambda x: (x > 0) - (x < 0)

        if abs(self.win_progress) == 4:
            return Player(_signum(self.win_progress))
        else:
            return Player.EMPTY

    @property
    def whole_move(self) -> int:
        return self.ply // 2 + 1

    @property
    def static_evaluation(self) -> float:
        return (
            sum(
                piece.player.value * weight
                for piece, weight in zip(self.board, Position.PIECE_WEIGHTS)
            )
            / 10
        )


def pgn(moves: Sequence[Move]) -> str:
    return "\n".join(
        f"{n}. {' '.join(str(move).ljust(4) for move in moves)}"
        for n, moves in enumerate(batched(moves, 2), start=1)
    )


A1 = Square(1, 1)
A2 = Square(1, 2)
A3 = Square(1, 3)
A4 = Square(1, 4)
A5 = Square(1, 5)
A6 = Square(1, 6)
A7 = Square(1, 7)
A8 = Square(1, 8)

B1 = Square(2, 1)
B2 = Square(2, 2)
B3 = Square(2, 3)
B4 = Square(2, 4)
B5 = Square(2, 5)
B6 = Square(2, 6)
B7 = Square(2, 7)
B8 = Square(2, 8)

C1 = Square(3, 1)
C2 = Square(3, 2)
C3 = Square(3, 3)
C4 = Square(3, 4)
C5 = Square(3, 5)
C6 = Square(3, 6)
C7 = Square(3, 7)
C8 = Square(3, 8)

D1 = Square(4, 1)
D2 = Square(4, 2)
D3 = Square(4, 3)
D4 = Square(4, 4)
D5 = Square(4, 5)
D6 = Square(4, 6)
D7 = Square(4, 7)
D8 = Square(4, 8)

E1 = Square(5, 1)
E2 = Square(5, 2)
E3 = Square(5, 3)
E4 = Square(5, 4)
E5 = Square(5, 5)
E6 = Square(5, 6)
E7 = Square(5, 7)
E8 = Square(5, 8)

F1 = Square(6, 1)
F2 = Square(6, 2)
F3 = Square(6, 3)
F4 = Square(6, 4)
F5 = Square(6, 5)
F6 = Square(6, 6)
F7 = Square(6, 7)
F8 = Square(6, 8)

G1 = Square(7, 1)
G2 = Square(7, 2)
G3 = Square(7, 3)
G4 = Square(7, 4)
G5 = Square(7, 5)
G6 = Square(7, 6)
G7 = Square(7, 7)
G8 = Square(7, 8)

H1 = Square(8, 1)
H2 = Square(8, 2)
H3 = Square(8, 3)
H4 = Square(8, 4)
H5 = Square(8, 5)
H6 = Square(8, 6)
H7 = Square(8, 7)
H8 = Square(8, 8)


# fmt: off
winning_board = [
#      a       b       c       d       e       f       g       h
    # _P(0) , _P(0) , _P(0) , _P(0) , _P(-1), _P(-1), _P(-1), _P(-1),  # 8
    # _P(0) , _P(0) , _P(0) , _P(0) , _P(0) , _P(-1), _P(-1), _P(-1),  # 7
    # _P(0) , _P(0) , _P(0) , _P(0) , _P(0) , _P(0) , _P(-1), _P(-1),  # 6
    # _P(0) , _P(0) , _P(0) , _P(-1), _P(1) , _P(0) , _P(0) , _P(-1),  # 5
    # _P(1) , _P(0) , _P(0) , _P(1) , _P(1) , _P(0) , _P(0) , _P(0) ,  # 4
    # _P(1) , _P(1) , _P(0) , _P(0) , _P(0) , _P(0) , _P(0) , _P(0) ,  # 3
    # _P(1) , _P(1) , _P(1) , _P(0) , _P(0) , _P(0) , _P(0) , _P(0) ,  # 2
    # _P(1) , _P(1) , _P(1) , _P(1) , _P(0) , _P(0) , _P(0) , _P(0) ,  # 1
]
# fmt: on

# p = Position(board=winning_board)
# print(p, p.win_progress, p.winner, sep="\n\n")

move_list = (
    Move(B1, D3),
    Move(G8, E6),
    Move(C1, E5),
    Move(E8, E4),
    Move(A1, E3),
    Move(F7, D5),
    Move(),
)
print(pgn(move_list))

p = Position()
print()
print(p)
print()
for move in move_list:
    p.move(move)
    print(p)
    print()
