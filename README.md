# GenAIwithDjangoRestApi

GenAIwithDjangoRestApi is a backend project built with Django REST Framework to support frontend and mobile apps with generative AI capabilities, document intelligence, chatbots, and weather analysis. It provides secure user authentication and a suite of agent-powered endpoints that frontend and mobile developers can easily integrate.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [API Overview](#api-overview)
- [Authentication & User Management](#authentication--user-management)
- [Agent Apps](#agent-apps)
  - [Chat Agent](#chat-agent)
  - [Document Agent](#document-agent)
  - [Weather Agent](#weather-agent)
- [How to Run Locally](#how-to-run-locally)
- [Frontend/Mobile Integration Guide](#frontendmobile-integration-guide)
- [Folder Structure](#folder-structure)
- [Contribution Guide](#contribution-guide)
- [License](#license)
- [Contact](#contact)

---

## Features

- **JWT-based User Registration, Login, and Password Change**
- **Chat Agent**: AI-powered chat endpoint for natural conversations
- **Document Agent**: Upload, vectorize, query, summarize, and analyze PDF documents
- **Weather Agent**: Query real-world weather, get AI-powered summaries, activity suggestions, and health tips
- **RESTful APIs**: Designed for easy use in web and mobile applications
- **CORS Enabled**: Works seamlessly with frontend frameworks and mobile apps

---

## Tech Stack

- **Backend**: Django, Django REST Framework, Channels
- **Database**: SQLite (default), MongoDB (for agent memory), can be changed to PostgreSQL/MySQL
- **Authentication**: JWT (rest_framework_simplejwt)
- **AI Models**: LLM via Ollama, LangChain agents
- **Other**: Redis (caching), Celery (task queue), drf-spectacular (API docs)

---

## API Overview

### User Authentication & Management (`user_auth`)
- `POST /accounts/api/v1/register/` — Register new users, with email and username uniqueness validation
- `POST /accounts/api/v1/token/` — Obtain access and refresh JWT (login)
- `POST /accounts/api/v1/token/refresh/` — Refresh JWT
- `GET /accounts/api/v1/user/` — Get current user's profile (JWT required)
- `PUT /accounts/api/v1/user/` — Update profile info (JWT required)
- `POST /accounts/api/v1/change_password/` — Change password securely (JWT required)

Password validation uses Django’s built-in validators plus custom checks for similarity, length, and common passwords.

### Chat Agent (`chat`)
- AI-powered chat endpoint for conversational features (see `chat` app).

### Document Agent (`documents`)
- `POST /documents/api/v1/upload/` — Upload PDF, vectorize and index for queries
- `POST /documents/api/v1/query/<session_id>/` — Ask questions about uploaded docs, get summaries, data analysis, and graphs

### Weather Agent (`weather_Agent`)
- `POST /weather_analysis/api/v1//<session_id>/` — Ask about any city’s weather, get real-time conditions plus AI analysis, activity suggestions, and health tips

---

## Authentication & User Management

- **JWT Authentication**: All protected endpoints require the Authorization header:
  ```
  Authorization: Bearer <your_jwt_token>
  ```
- **Registration**: Requires username, email, password, password confirmation.
- **Password Change**: Validates old password, enforces strong password policies.
- **Profile Update**: Allows updating user details via authenticated request.

---

## Agent Apps

### Chat Agent
- Handles conversational AI using an LLM backend.
- Suitable for integrating chatbot features in frontend/mobile apps.

### Document Agent
- Upload PDFs, automatically vectorized for semantic search and QA.
- Endpoints for querying, summarizing, extracting/analyzing data (means, sums, min/max, etc.), and generating graphs from document data.
- Uses LangChain tools and MongoDB-backed conversation memory to maintain session context.

### Weather Agent
- Accepts a city name and returns:
  - Real-time weather data (from wttr.in)
  - AI-generated summary of conditions
  - Suggested activities (indoors/outdoors)
  - Health tips (e.g., hydration, clothing, sun protection)
- Uses LangChain agent and custom tools for weather retrieval and analysis.

---

## How to Run Locally

1. **Clone the Repository**
   ```bash
   git clone https://github.com/minasielemma/GenAIwithDjangoRestApi.git
   cd GenAIwithDjangoRestApi
   ```

2. **Create Virtual Environment & Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

4. **Start the Server**
   ```bash
   python manage.py runserver
   ```



---

## Frontend/Mobile Integration Guide

- **All endpoints return JSON.**
- **CORS** is enabled for easy integration.
- Use standard fetch/HTTP libraries (Axios, fetch, Flutter http, etc.).
- For AI endpoints (chat, weather, document), POST with:
  ```json
  { "question": "What is the weather in Paris?" }
  ```
  and supply `Authorization: Bearer <token>`.

---

## Folder Structure

```
GenAIwithDjangoRestApi/
├── chat/              # Chat agent app
├── user_auth/         # User registration, login, profile, password change
├── documents/         # Document upload, query, summarize, analyze
├── weather_Agent/     # Weather analysis agent
├── core/              # Shared agent logic, LLM integration
├── manage.py
├── requirements.txt
├── README.md
└── ...
```

---

## Contribution Guide

1. Fork the repo & create a feature branch.
2. Make your changes (docs, code, tests).
3. Submit a pull request with a clear description.

---

## License

MIT License.

---

## Contact

- **Maintainer**: [minasielemma](https://github.com/minasielemma)
- **Issues**: [GitHub Issues](https://github.com/minasielemma/GenAIwithDjangoRestApi/issues)

---

Happy coding! 🚀
