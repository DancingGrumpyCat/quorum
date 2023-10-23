# Quorum

A Python implementation of one of my abstract games.

## Rules

Two players, **White** and **Black**, alternate _plays_, with **White** having the first play. Each player starts with 10 pieces called _stones_ placed on the 8×8 square board, as such:

```
   a b c d e f g h
8  · · · · ● ● ● ●
7  · · · · · ● ● ●
6  · · · · · · ● ●
5  · · · + + · · ●
4  ○ · · + + · · ·
3  ○ ○ · · · · · ·
2  ○ ○ ○ · · · · ·
1  ○ ○ ○ ○ · · · ·
```

## Definitions

- **You** are the player whose turn it is. Your **opponent** is the other player.
- A **stone** can be dark (belonging to **Black**) or light (belonging to **White**). (In this file, White stones are displayed as hollow circles ○ and Black stones are displayed as filled circles ●. This may be confusing for dark mode users; my apologies if so.) A stone is a **friend stone** if it matches your color. Otherwise, it is an **opponent stone**. 
- A **square** is one of the 64 territories on the board, and may contain up to 1 stone. A square is empty if it has no stone on it. A square is yours if it has your stone on it. Two squares are **adjacent** if they share an edge or a corner. A square's name is its file letter and its rank number (for example, "`a3`").
- A **file** is a vertical group of 8 squares. There are 8 files, named `a`-`h`.
- A **rank** is a horizontal group of 8 squares. There are 8 ranks, named `1`-`8`.
- Each player has a **home**. A home is a group of 4 squares closest to its owner's starting corner. That is, **White**'s home is the squares `a1`, `a2`, `b1`, and `b2`; and **Black**'s home is the squares `h8`, `h7`, `g8`, and `g7`.
- The objective squares are `d4`, `d5`, `e4`, and `e5`.
- There are two kinds of **plays**:
    - **movement** is moving a stone
    - **placement** is placing new stones

### Movement

To move, choose two of your stones. Choose one of those stones to be the active stone (the one that moves). The other stone is the center (the stone moved over). Move the active stone over the center, and then repeat that motion exactly, landing on the target square. For example, **White** `a1` can use `c2` as a pivot, landing on `e3`.

1. `a1e3`

```
   a b c d e f g h
8  · · · · ● ● ● ●
7  · · · · · ● ● ●
6  · · · · · · ● ●
5  · · · + + · · ●
4  ○ · · + + · · ·
3  ○ ○ · · ○ · · ·
2  ○ ○ ○ · · · · ·
1  · ○ ○ ○ · · · ·
```

You may only do a movement if all of the following are true:
- Ownership: you own both the active and center stones
- Space: the target square is empty and within the board area
- Distance: there is no more than 1 rank/file separating the target and center stones' ranks/files

After a movement, first do all possible suffocation effects simultaneously and instantaneously, and second do all possible conversion effects simultaneously and instantaneously. *These effects only happen to opponent stones as a result of the active stone moving; neither the active stone nor any friendly stones are ever suffocated or converted*.

#### Suffocation

Any opponent stone adjacent to the active stone is suffocated if it has no empty squares adjacent to it.

Example: a White stone moving to **A** suffocates `f4`. It does not suffocate the friendly e4 stone, and it does not suffocate itself. If `e4` were instead a Black stone, it would also be suffocated, since all suffocations happen instantaneously.

```
   a b c d e f g h
8  · · · · · · · ·
7  · · · · · · · ·
6  · · · · · · · ·
5  · · · ○ ● ● ● ·
4  · · · ● ○ ● ● ·
3  · · · ○ ○ A ○ ·
2  · · · · ○ ○ ○ ·
1  · · · · · · · ·
```

When you suffocate a stone, remove it from the board.

#### Conversion

Any opponent stone adjacent to the active stone that is also adjacent to a friendly stone immediately opposite the active stone is converted to your color.


```
   a b c d e f g h
8  · · · · · · · ·
7  · · · ○ · · · ·
6  · · · · ● A · ·
5  · · · + ● ● · ·
4  · · · ○ ○ ● · ·
3  · · · · · ○ · ·
2  · · · · · · · ·
1  · · · · · · · ·
```

Example: a White stone moving to **A** converts `e5`, but not `e6` (since there is no White stone on `d6`) and neither `f4` nor `f5` (they are sandwiched between two White stones, but not immediately so).

When you convert a stone, remove it from the board and replace it with one of your color.


### Placement

Instead of moving, you may place new stones. To do so, at least one of your home squares must be empty. Then, place a new stone of your color on each of your empty home squares.

### Winning

After both suffocation and conversion, you have won the game if the objective squares (`d4`, `d5`, `e4`, and `e5`) are all yours.