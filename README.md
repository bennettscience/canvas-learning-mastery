# Learning Mastery Grades Calculator

This Flask application hooks into Canvas to associate Outcome scores with actual assignments.

This is very much a work in progress.

## What does it do?

If you want to use Outcomes to dictate assignment scores, you have to do that one by one by hand in the gradebook. This means either using a dual-monitor setup to open both at the same time or clicking back and forth for each and every assignment. This app creates a relationship between an assignment and an outcome and then uses the Canvas API to update the gradebook in bulk.

Here's a practical example:

Outcome 1.1 defines a skill students should have. An Outcome score of 3.0 is considered 'passing.' Assignment 1.1 in the traditional gradebook is set to 1/1 when a 3.0 is reached on the Outcome. Currently, you have to update this score by hand.

This app allows the instructor to set a relationship between a single Outcome and an Assignment. When the mastery score is reached on the Outcome, the Assignment is automatically toggled to full credit for each student.

## What about student data?

No student data is stored in the app. The database is used to map an Outcome to an Assignment (and vice versa) using the item ID from Canvas. When the app runs, the stored IDs are queried and loaded into the dashboard for the user. Student scores are updated in real time via the API. As soon as the user logs out, the student data is cleared from the session.

## Dependencies

`pip install -r requirements.txt`

## Canvas Setup

This uses OAuth to log the user in directly to Canvas. You will need to go to your Canvas installation and add a Developer Key in the Admin console.

The app is configured to redirect to a `localhost` address. If this is being deployed on a web server, make sure to update the URL in the Developer Key options as well as in the config file.

## Config

Set up your config with `cp config-example.py config.py` in your directory. Update your config file with your Canvas Developer Key specifics. Make sure you edit your URL root in each of the URLs listed.

The API calls to Canvas are all done with [UCF Open's CanvasAPI library](https://github.com/ucfopen/canvasapi/tree/master).

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
