use std::collections::HashMap;
use std::fs;
use std::path::Path;

use serde::Deserialize;
use thiserror::Error;

use crate::model::{LayerSpec, MaterialSpec};

#[derive(Debug, Deserialize)]
struct CatalogBody {
    materials: Vec<MaterialSpec>,
}

#[derive(Debug, Error)]
pub enum MaterialError {
    #[error("failed to read catalog: {0}")]
    Io(#[from] std::io::Error),
    #[error("failed to parse catalog: {0}")]
    Parse(#[from] serde_json::Error),
    #[error("unknown physics_id {0}")]
    UnknownPhysicsId(u32),
    #[error("unknown asset_name {0}")]
    UnknownAssetName(String),
}

#[derive(Debug, Clone)]
pub struct MaterialCatalog {
    by_id: HashMap<u32, MaterialSpec>,
    by_asset: HashMap<String, MaterialSpec>,
}

impl MaterialCatalog {
    pub fn load(path: &Path) -> Result<Self, MaterialError> {
        let raw = fs::read_to_string(path)?;
        let body: CatalogBody = serde_json::from_str(&raw)?;
        let mut by_id = HashMap::new();
        let mut by_asset = HashMap::new();
        for mat in body.materials {
            by_asset.insert(mat.asset_name.clone(), mat.clone());
            by_id.insert(mat.physics_id, mat);
        }
        Ok(Self { by_id, by_asset })
    }

    pub fn by_physics_id(&self, physics_id: u32) -> Result<&MaterialSpec, MaterialError> {
        self.by_id
            .get(&physics_id)
            .ok_or(MaterialError::UnknownPhysicsId(physics_id))
    }

    pub fn resolve_layer(&self, layer: &LayerSpec) -> Result<&MaterialSpec, MaterialError> {
        if let Some(label) = &layer.asset_label {
            return self
                .by_asset
                .get(label)
                .ok_or_else(|| MaterialError::UnknownAssetName(label.clone()));
        }
        self.by_physics_id(layer.physics_id)
    }

    #[allow(dead_code)]
    pub fn resolve_asset_name(&self, name: &str) -> Result<&MaterialSpec, MaterialError> {
        self.by_asset
            .get(name)
            .ok_or_else(|| MaterialError::UnknownAssetName(name.to_string()))
    }
}
