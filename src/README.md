# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Students can view participants; teachers sign students up or unregister them
- Teacher login protects all registration changes

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

   In a separate terminal, create a teacher account from the `src` directory:

   ```
   python create_teacher.py
   ```

   The password is prompted securely and stored as a salted PBKDF2 hash in
   `teachers.json`. This file is ignored by Git. Set `TEACHERS_FILE` to use a
   different path. Teacher sessions are held in memory and expire after eight
   hours; restarting the server signs teachers out.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/me`                                                        | Check whether the current browser is signed in as a teacher          |
| POST   | `/auth/login`                                                     | Sign in as a teacher and receive an HttpOnly session cookie          |
| POST   | `/auth/logout`                                                    | End the current teacher session                                      |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student signup                                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only unregister                                         |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and participant data is stored in memory and resets when the server
restarts. Teacher credentials are stored separately in `teachers.json`.
