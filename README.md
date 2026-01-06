# StocksApp API Service ☁️

The backend REST API for the **StocksApp** mobile application.
Built with **FastAPI** (Python) and **MongoDB**, deployed on **Render**.

This service handles user authentication, stock data management, historical data tracking, and user watchlists.

## 🛠 Tech Stack

* **Language:** Python 
* **Framework:** FastAPI
* **Database:** MongoDB Atlas (Cloud)
* **Authentication:** JWT (JSON Web Tokens)
* **Deployment:** Render
* **Libraries:** `pymongo`, `uvicorn`, `python-dotenv`, `passlib`, `pyjwt`

## 🔗 Base URL

> **Production:** `https://stocks-server-e1vy.onrender.com/`

## 📡 API Endpoints

All endpoints (except `/health` and `/auth`) require a **Bearer Token** in the Authorization header.

### 1. General
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Check API status |

### 2. Authentication
| Method | Endpoint | Description | Body |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user | `{ "email": "...", "password": "..." }` |
| `POST` | `/auth/login` | Login and receive JWT | `{ "email": "...", "password": "..." }` |

### 3. Stocks Data
| Method | Endpoint | Description | Body / Params |
| :--- | :--- | :--- | :--- |
| `GET` | `/stocks` | Get list of all stocks | - |
| `POST` | `/stocks/seed` | Create/Update a stock | `{ "symbol": "AAPL", "price": 150.0 }` |
| `GET` | `/stocks/{symbol}/quote` | Get specific stock details | Path param: `symbol` |

### 4. Historical Data (Charts)
| Method | Endpoint | Description | Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/stocks/{symbol}/history` | Get history points | Path param: `symbol` |
| `POST` | `/stocks/history` | Upload full history | `{ "symbol": "...", "points": [...] }` |
| `POST` | `/stocks/{symbol}/history/append` | Add single point | `{ "ts": 12345, "price": 100, "volume": 50 }` |

### 5. Watchlist
| Method | Endpoint | Description | Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/watchlist` | Get user's watchlist | - |
| `POST` | `/watchlist` | Add stock to watchlist | `{ "symbol": "NKE" }` |
| `DELETE` | `/watchlist/{symbol}` | Remove stock | Path param: `symbol` |

## 🚀 How to Run Locally

### Prerequisites
* Python 3.x installed
* MongoDB Atlas connection string

### Installation

1.  **Clone the repository** and navigate to the server folder.

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Environment Variables:**
    Create a `.env` file in the root directory:
    ```env
    MONGO_URI=your_mongodb_connection_string
    DB_NAME=stockdb
    JWT_SECRET=your_secret_key_here
    ```

4.  **Run the server:**
    ```bash
    uvicorn main:app --reload
    ```

5.  **Open Documentation:**
    Go to `http://127.0.0.1:8000/docs` to see the automatic Swagger UI.

## 📄 License
This project is licensed under the MIT License.
