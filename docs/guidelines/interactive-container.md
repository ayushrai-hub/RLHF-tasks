# Interactive Container

Debug tasks before writing `solve.sh`.

```bash
harbor tasks start-env -p <task-folder> -i
# or: stb harbor tasks start-env -p <task-folder> -i
```

Inside container:

- Navigate filesystem
- Run solution commands manually
- Verify paths and dependencies

Exit: `exit`

## Tips

- Test every command manually before adding to `solve.sh`
- Verify all `instruction.md` paths exist
- Confirm deps installed in Dockerfile
- Copy working commands into oracle solution

## Common Issues

| Issue | Fix |
|-------|-----|
| Container won't start | Docker running; socket enabled (macOS) |
| Missing packages | Add to Dockerfile, rebuild |
| Wrong WORKDIR | Set `WORKDIR` in Dockerfile |
