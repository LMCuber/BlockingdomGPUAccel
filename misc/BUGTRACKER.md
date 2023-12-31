# Logical Bugs
## - Some entities rewinding to previous chunk for no reason
### Reproduced
When the velocity of the entity gets to 1 + the ground velocity at the same time as the entity transitioning into a new chunk
### Reason
When the entity moves in the x-axis, it may encounter a new chunk. However, the chunk updating only updates after the update function of the entity, so it doesn't update when the entity has to move in the y-direction. This way, the entity gets faulty chunk information and doesn't detect any collision in the y-axis. This means that the next frame (when the entity gets the correct chunk information), the x-axis collision will trigger, making the player move left, as if it hit a wall. This causes the rewind.
### Solution
1. Update the y-axis of the entity first to sync it with the chunk relocation logic
2. Fix the neighbour detection when overlapping chunks, it is harder so I will stick to 1 for now, but I might refactor it

## - Unknown metadata for some known data at given position
### Reproduced
When applying world_modifications in the generate_chunk function
### Reason
world_modifications generates structures that overextend outside the chunk, which do not have any metadata equivalent
### Solution
Ignore those blocks lmao

## - Some mobs not updating
### Reproduced
When the mobs are too deep underground
### Reason
The mobs belong to a chunk, so when the chunk doesn't update anymore,
the mobs don't either
### Solution
~~Save mobs in a global list rather than in a list per chunk (?)~~
This is very resource-heavy. Just don't update the mobs, _or_ have a larger range for mob detection. For example, is the chunks update in a [-2, 2] range, the mobs will update in the [-5, 5] range. But I will look into this.

## - You cannot break some blocks
### Reproduced
The blocks have to be extending out of a chunk border
### Reason
Because of the way world generation works, the blocks can be placed outside a chunk.
Whenever you click on it, the game detects it and thinks that you want the block at that position, which
is another block in another chunk.
### Solution
_In progress_

# Graphical Bugs
...
