# How to work in this vault

This folder is an Obsidian vault. Every note is a markdown file. Read this
before any task here.

## About me

- What I do: <one line about your business or work>
- What I want from my notes: <e.g. turn ideas into next steps I can act on this week>

## Folders

| Folder | What is in it | Claude may |
|---|---|---|
| `Inbox/` | Raw thoughts, unsorted | Read. Move only when I say so |
| `Ideas/` | One idea per note | Read. Edit only when I say so |
| `Meetings/` | One note per call | Read |
| `Projects/` | Things with a finish line | Read. Edit only when I say so |
| `Reference/` | Facts I look up | Read |
| `Private/` | Off limits | Nothing (blocked in .claude/settings.json) |
| `Claude/` | Everything Claude writes | Read and write |

## Rules

- Write new notes in `Claude/`, never over my notes.
- Never delete anything. List possible duplicates instead.
- Never invent facts, numbers, names or decisions. Anything you add that is
  not in my notes is marked `(suggestion)`.
- Every note you write starts with:

  ```
  ---
  source: "[[Original note]]"
  created: YYYY-MM-DD
  by: claude
  ---
  ```

- Link with `[[Note name]]`, tasks as `- [ ]`, keep note names readable.
- At the end, list which notes you read, which you wrote, and any of my notes
  you changed.
