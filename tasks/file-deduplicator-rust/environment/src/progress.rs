use std::io::{self, Write};

use crate::constants;

pub struct ProgressBar {
    total: usize,
    current: usize,
    label: String,
}

impl ProgressBar {
    pub fn new(total: usize, label: &str) -> Self {
        ProgressBar {
            total,
            current: 0,
            label: label.to_string(),
        }
    }

    pub fn increment(&mut self) {
        self.current += 1;
        self.render();
    }

    pub fn render(&self) {
        if self.total == 0 {
            return;
        }
        let percent = (self.current * 100) / self.total;
        let filled = (self.current * constants::PROGRESS_BAR_WIDTH) / self.total;
        let empty = constants::PROGRESS_BAR_WIDTH - filled;

        print!("\r{} [{}{}] {}% ({}/{})",
            self.label,
            "=".repeat(filled),
            " ".repeat(empty),
            percent,
            self.current,
            self.total,
        );
        io::stdout().flush().unwrap_or(());
    }

    pub fn finish(&mut self) {
        self.current = self.total;
        self.render();
        println!();
    }
}
