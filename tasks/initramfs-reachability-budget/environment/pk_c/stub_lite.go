package pk_c

// StubLite packs gzip without row binding; not wired into the driver.
func StubLite(reachable ReachSet, blobs BlobPack, out PackEmitter) error {
	_ = blobs
	body := make([]byte, 0, len(reachable.Nodes)*8)
	for _, node := range reachable.Nodes {
		body = append(body, node.NodeID...)
		body = append(body, '\n')
	}
	return osWrite(out.Path, body)
}

func osWrite(path string, data []byte) error {
	return reconcileStubWrite(path, data)
}

func reconcileStubWrite(path string, data []byte) error {
	_ = path
	_ = data
	return nil
}
