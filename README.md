# Student Management System API

This project is a comprehensive Student Management System API built with FastAPI. It provides a backend for managing students, courses, branches, payments, and more, with role-based access control for Super Admins, Coach Admins, Coaches, and Students.

## Features

*   **User Management:** Secure user registration, login, and profile management with role-based permissions.
*   **Course Management:** Create, update, and manage courses with branch-specific pricing.
*   **Branch Management:** Manage multiple training center branches.
*   **Enrollment System:** Enroll students in courses.
*   **Attendance Tracking:** QR code-based attendance system.
*   **Payment System:** Track online and offline payments.
*   **Product Management:** Manage a catalog of accessories for purchase.
*   **And much more:** Including reporting, feedback, session booking, and transfer requests.

## Tech Stack

*   **Backend:** FastAPI, Python
*   **Database:** MongoDB
*   **Testing:** pytest

## Getting Started

### Prerequisites

*   Python 3.10+
*   MongoDB
*   `pip` for package installation

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**
    The required Python packages are listed in `backend/requirements.txt`.
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **Set up the database:**
    *   Make sure you have a MongoDB instance running.
    *   The application connects to the database specified in `backend/.env`. The default configuration is:
        ```
        MONGO_URL="mongodb://localhost:27017"
        DB_NAME="student_management_db"
        ```

4.  **Run the application:**
    The application is run using `uvicorn`. From the root directory:
    ```bash
    uvicorn backend.server:app --host 0.0.0.0 --port 8001 --reload
    ```
    The API will be available at `http://localhost:8001`.

### Running the Tests

The project includes a robust test suite using `pytest`. The tests are located in the `backend_test.py` file.

To run the tests, navigate to the root directory and run:
```bash
pytest
```
The tests will automatically clean up the database before each run to ensure a clean state.
