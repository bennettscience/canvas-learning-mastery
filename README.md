# Learning Mastery Grades Doctor

This Flask application hooks into Canvas to associate Outcome scores with actual assignments.

This is very much a work in progress.

The API calls to Canvas are all done with [UCF Open's CanvasAPI library][https://github.com/ucfopen/canvasapi/tree/master].

## TODO

### Backend

- [x] Database models
  - [x] outcomes
  - [x] assignments
  - [ ] Configs table
- [x] Link assignment to outcome
- [ ] Per-student reporting
- [x] Routing
  - [X] Login required view
  - [X] standardize `id` structures
  - ~~[ ] Student view?~~
- [x] Update assignment scores on Canvas

### Authentication

- [X] OAuth2 Login
- [X] `Canvas` object for API calls

### Frontend

- [ ] navbar
- [ ] App config settings
- [ ] Canvas URL
- [x] Dashboard
  - [X] Course picker
- [x] Course
  - [x] Define assignment category ID
    - [x] Fetch assignments in the group
  - [x] Import course outcomes by group
