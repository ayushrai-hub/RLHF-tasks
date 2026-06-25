export const DB_PATH_DEFAULT      = '/app/data/sensors.db';
export const DOSSIER_PATH_DEFAULT = '/app/docs/seismology_ops_dossier.md';
export const OUTPUT_PATH_DEFAULT  = '/app/output/events.json';

// See seismology_ops_dossier.md §9 for derivation of these constants.
export const PRESSURE_TO_DISPLACEMENT_M_PER_KPA = 0.1;
export const MAD_CONSISTENCY_CONSTANT = 1.4826;
export const DETREND_WINDOW_SAMPLES = 10 * 24 * 6;
