from contextlib import suppress
from enum import Enum
from itertools import (  # type: ignore
    batched,
    zip_longest,
)
from typing import ClassVar, Optional, Self, Sequence


class DisplayStyle:
    """
    Only used to modify the printing of Quorum positions.
    Can modify the piece presentation, the empty squares presentation, the vertical
    separator between the board and the extra information, and the rank and file
    symbols.

    ### Example
    ```py
    greek = DisplayStyle("●○·", "⎸", files="αβγδεζηθ")
    uppercase_ascii = DisplayStyle("XO.", "|", files="ABCDEFGH")
    """

    def __init__(
        self,
        /,
        *,
        pieces: str,
        placement: str = "+",
        from_to_separator: str = "",
        sep: str,
        files: str = "abcdefgh",
        ranks: str = "12345678",
    ) -> None:
        self.pieces = pieces
        self.placement = placement
        self.from_to_separator = from_to_separator
        self.sep = sep
        self.files = files
        self.ranks = ranks
        self.move_width = max(4 + len(from_to_separator) + 1, len(placement))


class Styles(Enum):
    circles = DisplayStyle(pieces="●○·", placement="++", from_to_separator="-", sep="⎸")
    lowercase_ascii = DisplayStyle(pieces="xo.", sep="|")
    uppercase_ascii = DisplayStyle(pieces="XO.", sep="|", files="ABCDEFGH")
    greek = DisplayStyle(pieces="●○·", sep="⎸", files="αβγδεζηθ")


DEFAULT_STYLE = Styles.circles.value


class Player(Enum):
    """
    ### Player
    Can be `Black`, `White`, or `Empty` (for example, describing the winning player in a
    game that isn't finished).

    #### Home squares
    Each player has home squares that they can generate stones on.
    """

    BLACK = -1
    EMPTY = +0
    WHITE = +1

    def __str__(self) -> str:
        return self.name.capitalize()

    def __invert__(self) -> Self:
        if self is Player.EMPTY:
            raise ValueError("Cannot invert empty")
        return type(self)(-self.value)

    @property
    def home_squares(self) -> tuple:
        if self is Player.BLACK:
            return (H8, H7, G8, G7)
        if self is Player.WHITE:
            return (A1, A2, B1, B2)
        raise ValueError


class Piece:
    """
    ### Player
    Can be Black, White, or Empty (describing an empty square).
    """

    def __init__(
        self,
        player: Player | int,
        /,
        *,
        display_style: DisplayStyle = DEFAULT_STYLE,
    ) -> None:
        if isinstance(player, int):
            player = Player(player)
        self.player = player
        self.display_style = display_style

    def __invert__(self) -> Self:
        return type(self)(~self.player)

    def __str__(self) -> str:
        pieces = DEFAULT_STYLE.pieces
        match self.player:
            case Player.BLACK:
                return pieces[0]
            case Player.WHITE:
                return pieces[1]
            case Player.EMPTY:
                return pieces[2]

    def __repr__(self) -> str:
        return f"Piece({self.player})"

    @property
    def is_empty(self) -> bool:
        return self.player is Player.EMPTY


_P = Piece


class Line:
    """
    ### Line
    Utility class, superclass of Rank and File.
    """

    def __init__(self, value: int) -> None:
        self.value = value


class Rank(Line):
    """
    A horizontal line. __str__ returns `f"<{value}>"` if not inside the range 1-8.
    """
    def __str__(self) -> str:
        if not (1 <= self.value <= 8):
            return f"<{self.value}>"
        return DEFAULT_STYLE.ranks[self.value - 1]


class File(Line):
    """
    A vertical line. __str__ returns `f"<{value}>"` if not inside the range 1-8.
    """
    def __str__(self) -> str:
        if not (1 <= self.value <= 8):
            return f"<{self.value}>"
        return DEFAULT_STYLE.files[self.value - 1]


class Square:
    """
    Intersection type of Rank and File.
    """
    # fmt: off
    neighbors = (
        (-1, -1),
        (-1,  0),
        (-1, +1),
        ( 0, +1),
        (+1, +1),
        (+1,  0),
        (+1, -1),
        ( 0, -1),
    )
    # fmt: on

    def __init__(self, f: int, r: int, /) -> None:
        self.file: int = f
        self.rank: int = r

    @property
    def in_bounds(self) -> bool:
        # both file and rank must be between 1 and 8
        f, r = self.file, self.rank
        return 1 <= min(f, r) <= max(f, r) <= 8

    def __str__(self) -> str:
        return f"{File(self.file)}{Rank(self.rank)}"

    def __add__(self, other: Self | tuple[int, int]) -> Self:
        if isinstance(other, Square):
            file, rank = other.file, other.rank
        elif isinstance(other, tuple):
            file, rank = other
        else:
            raise TypeError
        return type(self)(self.file + file, self.rank + rank)

    def __floordiv__(self, n: int) -> Self:
        if isinstance(n, int):
            return type(self)(self.file // n, self.rank // n)
        raise TypeError("A Square can only be divided by an int.")

    __truediv__ = __floordiv__


class Move:
    """
    Either has both a move and an origin (for a movement) or neither (for a placement).
    """
    def __init__(
        self,
        origin: Optional[Square] = None,
        target: Optional[Square] = None,
    ) -> None:
        self.origin = origin
        self.target = target

        self.center: Optional[Square] = (
            (origin + target) / 2 if not (target is None or origin is None) else None
        )

    def __str__(self) -> str:
        return (
            f"{self.origin or DEFAULT_STYLE.placement}"
            f"{DEFAULT_STYLE.from_to_separator if self.target else ''}"
            f"{self.target or ''}"
        )


class GameEnd(Move):
    def __init__(self, winning_player: Player) -> None:
        self.winning_player = winning_player

    def __str__(self) -> str:
        match self.winning_player:
            case Player.BLACK:
                return "0-1"
            case Player.WHITE:
                return "1-0"
            case Player.EMPTY:
                return "½-½"


class Position:
    """
    Keeps track of a board, the current move number (ply), and the most recent move.
    Ply starts at 0, after White's first move becomes 1, and after Black's first move
    becomes 2.
    """

    # fmt: off
    START_BOARD: ClassVar[list[Piece]] = [
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

    PIECE_WEIGHTS: tuple[int, ...] = (
    #   a   b   c   d   e   f   g   h
        1,  1,  1,  1,  1,  1,  1,  1,  # 8
        1,  1,  1,  2,  2,  1,  1,  1,  # 7
        1,  1,  2,  5,  5,  2,  1,  1,  # 6
        1,  2,  5, 10, 10,  5,  2,  1,  # 5
        1,  2,  5, 10, 10,  5,  2,  1,  # 4
        1,  1,  2,  5,  5,  2,  1,  1,  # 3
        1,  1,  1,  2,  2,  1,  1,  1,  # 2
        1,  1,  1,  1,  1,  1,  1,  1,  # 1
    )
    # fmt: on

    def __init__(
        self,
        board: list[Piece] = START_BOARD,
        ply: int = 0,
        last_move: Optional[Move] = None,
    ) -> None:
        self.board = board.copy()
        self.ply = ply
        self.last_move = last_move

    def __str__(self) -> str:
        if self.winner is Player.EMPTY:
            to_move_str = f"{Piece(self.to_move.value)} to move"
        else:
            to_move_str = f"{Piece(self.winner.value)} wins by quorum"
        extras = (
            to_move_str,
            f"Move: {self.whole_move} (ply {self.ply})",
            f"Last move: {self.last_move}",
            f"Win progress: {self.win_progress}",
            f"Static evaluation: {self.static_evaluation}",
        )

        sep = f"  {DEFAULT_STYLE.sep}  "

        return f"  {' '.join(DEFAULT_STYLE.files)}{sep}\n" + "\n".join(  # type: ignore
            f"{DEFAULT_STYLE.ranks[7 - int(i)]} "
            + " ".join(str(c) for c in row)
            + sep
            + extra
            for (i, row), extra in zip_longest(
                enumerate(batched(self.board, n=8)), extras, fillvalue=""
            )
        )

    def __getitem__(self, square: Square) -> Piece:
        return self.board[square.file - (8 * square.rank) + 63]

    def __setitem__(self, square: Square, new_piece: Piece) -> Self:
        board = self.board
        board[square.file - (8 * square.rank) + 63] = new_piece
        return type(self)(board)

    @property
    def to_move(self) -> Player:
        return Player.WHITE if self.ply % 2 == 0 else Player.BLACK

    def copy(self) -> Self:
        return type(self)(self.board, self.ply, self.last_move)

    def move(self, move: Move) -> Self:  # noqa: C901  # (function is too complex)
        new_pos = self
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
            for helper in (move.target + d for d in Square.neighbors):
                if self[helper].player is ~self.to_move:
                    for delta in Square.neighbors:
                        if not (hd := helper + delta).in_bounds:
                            continue
                        if self[hd].is_empty:
                            break
                    else:
                        self[helper] = Piece(Player.EMPTY)

            # do conversions
            for helper in (
                move.target + (x * 2, y * 2)  # noqa: RUF005
                for (x, y) in Square.neighbors
            ):
                with suppress(IndexError):
                    avg: Square = (helper + move.target) / 2
                    if (
                        not self[avg].is_empty
                        and ~self[avg].player is self[helper].player
                    ):
                        new_pos[avg] = Piece(self.to_move)

        new_pos.ply += 1
        new_pos.last_move = move

        return new_pos

    @property
    def win_progress(self) -> int:
        return sum(self[square].player.value for square in WIN_SQUARES)

    @property
    def winner(self) -> Player:
        def _signum(x: float | int) -> int:
            return (x > 0) - (x < 0)

        if abs(self.win_progress) == 4:
            return Player(_signum(self.win_progress))
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


def pgn(
    moves: Sequence[Move],
    result: Optional[GameEnd] = None,
) -> str:
    if result is not None:
        moves = (*moves, result)
    return "\n".join(
        f"{f'{n}.'.rjust(3)} "
        f"{' '.join(str(move).ljust(DEFAULT_STYLE.move_width) for move in moves)}"
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


WIN_SQUARES = (D4, D5, E4, E5)


def main() -> None:
    move_list = (
        Move(B1, D3),
        Move(G8, E6),
        Move(C1, E5),
        Move(E8, E4),
        Move(A1, E3),
        Move(F7, D5),
        Move(D1, F5),
        Move(H8, F6),
        Move(),
        Move(F8, F4),
        Move(C2, G4),
        Move(H7, H3),
        Move(A2, C4),
        Move(),
        Move(B2, D6),
        Move(H5, F3),
        Move(A1, C5),
        Move(H6, D4),
        Move(B1, B5),
        Move(G6, C6),
        Move(A3, E5),
        Move(H7, D5),
        Move(B3, D7),
        Move(G7, E5),
    )
    print(pgn(move_list, GameEnd(Player.BLACK)))

    p = Position()
    print()
    print(p)
    print()
    for move in move_list:
        p.move(move)
        print(p)
        print()


if __name__ == "__main__":
    main()
