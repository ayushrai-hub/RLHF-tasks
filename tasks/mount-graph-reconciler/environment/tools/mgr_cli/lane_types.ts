export interface MetaLane {
  clTag: string;
  sliceName: string;
  stubHex: string;
}

export interface LayoutLane {
  slots: Record<string, string>;
}

export interface RunCols {
  armId: string;
  clTag: string;
  passNum: number;
  stubHex: string;
}

export interface AuthPick {
  mode: string;
}

export interface ReportRow {
  armId: string;
  clTag: string;
  rowDigest: string;
  nodeTags: string[];
  pathAHex: string;
  pathBHex: string;
  crossLink: string;
}
