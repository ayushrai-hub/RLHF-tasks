use std::ffi::c_void;
use std::os::raw::{c_char, c_int, c_ulonglong};

extern "C" {
    fn batch_reset(batch: *mut c_void);
    fn batch_queue(batch: *mut c_void, cell_id: *const c_char, epoch: c_ulonglong);
    fn flush_t8(batch: *mut c_void, commit_epoch: c_ulonglong) -> c_int;
    fn batch_last_commit_epoch(batch: *const c_void) -> c_ulonglong;
}

pub struct ActuatorBridge {
    storage: [u8; 2048],
}

impl ActuatorBridge {
    pub fn new() -> Self {
        let mut bridge = Self {
            storage: [0u8; 2048],
        };
        unsafe { batch_reset(bridge.as_mut_ptr()) };
        bridge
    }

    fn as_mut_ptr(&mut self) -> *mut c_void {
        self.storage.as_mut_ptr() as *mut c_void
    }

    fn as_ptr(&self) -> *const c_void {
        self.storage.as_ptr() as *const c_void
    }

    pub fn queue(&mut self, cell_id: &str, epoch: u64) {
        let c = std::ffi::CString::new(cell_id).unwrap();
        unsafe { batch_queue(self.as_mut_ptr(), c.as_ptr(), epoch) };
    }

    pub fn commit(&mut self, epoch: u64) -> i32 {
        unsafe { flush_t8(self.as_mut_ptr(), epoch) }
    }

    pub fn last_commit_epoch(&self) -> u64 {
        unsafe { batch_last_commit_epoch(self.as_ptr()) }
    }
}

pub fn digest_hex(cells: &[(String, u64)]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    for (id, epoch) in cells {
        hasher.update(id.as_bytes());
        hasher.update(epoch.to_le_bytes());
    }
    format!("{:x}", hasher.finalize())
}
