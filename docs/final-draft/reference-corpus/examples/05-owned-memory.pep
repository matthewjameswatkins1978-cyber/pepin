// PROPOSED PEP SYNTAX FIXTURE; safe manual allocation + bounded unsafe/device boundary.
use std.memory as memory
use std.device as device

pub fn fill_and_free() -> Result[Unit, memory.Error]
    uses memory.allocate, memory.write, memory.free
{
    var buffer = try memory.allocate[Byte](16)

    // Contextual numeric literal must fit Byte without an implicit narrowing cast.
    try memory.write(edit buffer, 0, 42)

    // Consuming transfer invalidates 'buffer' immediately.
    try memory.free(take buffer)
    Ok(())
}

// Danger grants *no* device authority. Only a host-granted MMIO capability
// plus a checked offset/alignment contract can justify this boundary.
pub fn read_register(region: device.MmioRegion, offset: Int) -> Int
    uses device.mmio
{
    danger {
        device.read_volatile(region, offset)
    }
}

// A successful compile must record which low-level obligations were proven
// and which were trusted FFI/device assumptions; it must never call the
// latter "proved". Exactly how the host validates MmioRegion is still open.
