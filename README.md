---
title: "BUNEC Request Management System"
emoji: "📋"
colorFrom: "blue"
colorTo: "indigo"
sdk: "docker"
sdk_version: "0.78.0"
app_file: "src/main.py"
pinned: false
---


# 📋 BUNEC Request Management System

## 🌟 Project Overview

**BUNEC** is a lightweight, secure, and efficient web application built with **FastAPI** 🚀 for managing requests for civil status documents (birth, marriage, and death certificates) and associated file uploads. Designed for minimalism, it focuses exclusively on creating, updating, retrieving, and deleting requests and documents, with secure communication to **Angara** using RSA public/private key encryption. No additional features (e.g., user management, payment processing, or center management) are included, per the project requirements.

### 🎯 Key Features
- **Request Management** 📄: Create, update, retrieve, and delete requests for birth, marriage, and death certificates.
- **Document Management** 📎: Upload and delete documents (JPEG, PNG) associated with requests.
- **Secure Communication** 🔒: Exchange encrypted data with **Angara** using RSA encryption.
- **Authentication** 🛡️: JWT-based authentication for client access.
- **Asynchronous Database Operations** 🗄️: Optimized for performance using SQLAlchemy with PostgreSQL.

## 🏗️ Architecture

BUNEC follows a **modular, asynchronous architecture** leveraging **FastAPI**, **SQLAlchemy Async**, and **PostgreSQL**. Key components include:

- **Routers** 🛤️: Dedicated endpoints for requests (`/birth`, `/marriage`, `/death`, `/requests`, `/documents`) and secure communication (`/keys`, `/comm`).
- **Schemas** 📑: Pydantic models for strict input/output validation (e.g., `BirthCertificateRequestCreate`, `RequestResponse`).
- **Database** 🗄️: Asynchronous SQLAlchemy with PostgreSQL, optimized with indexes for performance.
- **Security** 🔐: JWT authentication via `python-jose` and RSA encryption for Angara communication.
- **File Storage** 📂: Documents stored in `src/static` (configurable for cloud storage in production).

### 📂 Directory Structure
```
bunec/
├── src/
│   ├── api/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── routers.py          # FastAPI endpoints
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── services.py         # Business logic
│   ├── util/
│   │   ├── db/
│   │   │   ├── db.py           # Database configuration
│   │   │   ├── config.py       # Environment settings
│   │   ├── enums.py            # Enum definitions
│   ├── static/                 # Document storage
│   ├── main.py                 # FastAPI application entry point
├── migrations/                 # Alembic migrations
├── .env                        # Environment variables
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Dependencies
```

## 🛠️ Installation and Setup

### 📋 Prerequisites
- **Python**: 3.10+
- **PostgreSQL**: 13+
- **Dependencies**: Listed in `requirements.txt`
- **Optional**: `alembic`, `autoflake`, `isort`, `black` for migrations and code formatting

### 🚀 Installation Steps
1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd bunec
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install autoflake isort black  # For migration formatting
   ```

4. **Configure Environment**:
   - Copy the `.env` example to `.env` and update with your settings:
     ```bash
     cp .env.example .env
     ```
     Example `.env`:
     ```
     # Application
     ENV=dev
     BASE_URL=https://angara.vertex-cam.com

     # Database
     DB_USER=postgres
     DB_PASSWORD=your_password
     DB_HOST=localhost
     DB_PORT=5432
     DB_NAME=bunec
     DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/bunec

     # JWT Security
     SECRET_KEY=your_secret_key
     ALGORITHM=HS256
     ACCESS_TOKEN_EXPIRE_MINUTES=60

     # File Storage
     DOCUMENTS_STORAGE_PATH=src/static
     DOCUMENTS_SIZE=5
     LOGO_STORAGE_PATH=src/static
     ```

5. **Set Up Database**:
   - Create the database:
     ```bash
     createdb -U postgres bunec
     ```
   - Initialize Alembic migrations:
     ```bash
     alembic init migrations
     ```
   - Update `migrations/env.py`:
     ```python
     from src.api.models import Base
     target_metadata = Base.metadata
     ```
   - Generate and apply migrations:
     ```bash
     alembic revision --autogenerate -m "Initial migration"
     alembic upgrade head
     ```

6. **Clear Python Cache**:
   ```bash
   find . -name "__pycache__" -type d -exec rm -r {} +
   find . -name "*.pyc" -type f -exec rm -r {} +
   ```

7. **Run the Application**:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

8. **Access the API**:
   - **Swagger UI**: `http://localhost:8000/docs`
   - **Health Check**: `http://localhost:8000/health`

## 📡 API Endpoints

All endpoints require **JWT authentication** via `Authorization: Bearer <token>`. The `id` field is auto-generated and not required for request creation.

### 📄 Requests
- **POST /birth** 🆕: Create a birth certificate request.
- **POST /marriage** 🆕: Create a marriage certificate request.
- **POST /death** 🆕: Create a death certificate request.
- **GET /requests** 📋: Retrieve all requests (paginated).
- **GET /requests/{request_id}** 👁️: Retrieve a specific request.
- **PUT /requests/{request_id}** ✏️: Update a request.
- **DELETE /requests/{request_id}** 🗑️: Delete a request.
- **POST /search** 🔍: Search for a request by type, number, and center.

### 📎 Documents
- **POST /documents** 📤: Upload a document (JPEG, PNG) for a request.
- **DELETE /documents/{demande_id}** 🗑️: Delete a document.

### 🔑 Key Exchange
- **GET /keys/public-key** 🔍: Retrieve BUNEC’s public key.
- **POST /keys/set-public-key** ➕: Set Angara’s public key.

### 🔒 Secure Communication
- **POST /comm/send-request** 📩: Send an encrypted request to Angara.
- **POST /comm/receive-request** 📥: Receive and decrypt a request from Angara.

## 🔒 Security

- **JWT Authentication** 🔑: Validates client access using `python-jose`. Tokens are generated externally (e.g., via an auth system).
- **RSA Encryption** 🔐: Uses `cryptography` for secure data exchange with Angara.
- **File Validation** 📂: Restricts uploads to JPEG/PNG, with a 5MB size limit.
- **Database Security** 🗄️: Uses parameterized queries and connection pooling for stability.

## 🗄️ Database Schema

- **requests**: Stores request metadata (`id`, `numero_acte`, `type_demande`, `created_at`, `updated_at`, `numero_unique`, `nom_complet`, `ville`).
- **birth_certificate_requests**: Birth certificate details (e.g., `nom`, `date_naissance`, `pnd`).
- **marriage_certificate_requests**: Marriage certificate details (e.g., `epoux_nom`, `date_mariage`).
- **death_certificate_requests**: Death certificate details (e.g., `nom_decede`, `date_deces`).
- **documents**: Stores document metadata (`demande_id`, `nom_fichier`, `chemin_fichier`).

Indexes are applied to frequently queried fields (e.g., `numero_acte`, `nom_complet`, `date_naissance`) for performance.

## 🚀 Usage

### 👤 For Clients
1. **Obtain a JWT Token**:
   - Use an external auth system to generate a token.
   - Example: `curl -X POST http://<auth-system>/login -d '{"client_id": 123}'`
2. **Create a Request**:
   - Example for birth certificate:
     ```bash
     curl -X POST http://localhost:8000/birth \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      -d '{
          "numero_acte": "M-2025/030",
          "type_demande": "Acte de mariage",
          "created_at": "2025-07-07T10:00:00Z",
          "updated_at": "2025-07-07T10:00:00Z",
          "nom_complet": "TCHOUA Patrice & NGUIMATSIA Léa",
          "ville": "Bafang",
          "date_mariage": "2024-12-10",
          "lieu_mariage": "Hôtel de Ville de Bafang",
          "regime_matrimonial": "Communauté de biens",
          "epoux_nom": "TCHOUA Patrice",
          "epoux_date_naissance": "1991-04-22",
          "epoux_lieu_naissance": "Bafang",
          "epoux_profession": "Entrepreneur",
          "epoux_domicile": "Quartier Marché, Bafang",
          "epoux_pere": "TCHOUA Alain",
          "epoux_mere": "NDJOMO Elise",
          "epoux_chef_famille": "Oui",
          "temoin_epoux": "FONKOU Charles",
          "epouse_nom": "NGUIMATSIA Léa",
          "epouse_date_naissance": "1994-09-15",
          "epouse_lieu_naissance": "Dschang",
          "epouse_profession": "Secrétaire",
          "epouse_domicile": "Carrefour EEC, Dschang",
          "epouse_pere": "NGUIMATSIA Roland",
          "epouse_mere": "MBOA Thérèse",
          "epouse_chef_famille": "Non",
          "temoin_epouse": "TALLA Florence",
          "officier_etat_civil": "Mbarga Victor",
          "centre_etat_civil": "CECBA01",
          "assister_par": "Avocat Maître Mbiandou"
      }'
     ```

   - Example for marriage certificate:
     ```bash
     curl -X POST http://localhost:8000/marriage \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      -d '{
          "numero_acte": "M-2025/030",
          "type_demande": "Acte de mariage",
          "created_at": "2025-07-07T10:00:00Z",
          "updated_at": "2025-07-07T10:00:00Z",
          "nom_complet": "TCHOUA Patrice & NGUIMATSIA Léa",
          "ville": "Bafang",
          "date_mariage": "2024-12-10",
          "lieu_mariage": "Hôtel de Ville de Bafang",
          "regime_matrimonial": "Communauté de biens",
          "epoux_nom": "TCHOUA Patrice",
          "epoux_date_naissance": "1991-04-22",
          "epoux_lieu_naissance": "Bafang",
          "epoux_profession": "Entrepreneur",
          "epoux_domicile": "Quartier Marché, Bafang",
          "epoux_pere": "TCHOUA Alain",
          "epoux_mere": "NDJOMO Elise",
          "epoux_chef_famille": "Oui",
          "temoin_epoux": "FONKOU Charles",
          "epouse_nom": "NGUIMATSIA Léa",
          "epouse_date_naissance": "1994-09-15",
          "epouse_lieu_naissance": "Dschang",
          "epouse_profession": "Secrétaire",
          "epouse_domicile": "Carrefour EEC, Dschang",
          "epouse_pere": "NGUIMATSIA Roland",
          "epouse_mere": "MBOA Thérèse",
          "epouse_chef_famille": "Non",
          "temoin_epouse": "TALLA Florence",
          "officier_etat_civil": "Mbarga Victor",
          "centre_etat_civil": "CECBA01",
          "assister_par": "Avocat Maître Mbiandou"
      }'
     ```


   - Example for death certificate:
     ```bash
     curl -X POST http://localhost:8000/death \
      -H "Authorization: Bearer <token>" \
      -H "Content-Type: application/json" \
      -d '{
          "numero_acte": "D-2025/010",
          "type_demande": "Acte de décès",
          "created_at": "2025-07-07T11:00:00Z",
          "updated_at": "2025-07-07T11:00:00Z",
          "nom_complet": "ELOUNDOU Marie",
          "ville": "Ebolowa",
          "nom_decede": "ELOUNDOU Marie",
          "date_naissance": "1945-03-12",
          "lieu_naissance": "Ebolowa",
          "sexe": "féminin",
          "situation_matrimoniale": "Veuve",
          "profession": "Cultivatrice",
          "domicile": "Mvila, Ebolowa",
          "date_deces": "2025-06-01",
          "lieu_deces": "Centre de santé d’Ebolowa",
          "nom_pere": "ELOUNDOU Pierre",
          "nom_mere": "ABESSO Jeanne",
          "date_dressage": "2025-06-02",
          "declarant_nom": "ELOUNDOU André",
          "declarant_profession": "Enseignant",
          "declarant_qualite": "Fils",
          "premier_temoin_nom": "NGONO Pascal",
          "premier_temoin_profession": "Chef de village",
          "premier_temoin_residence": "Beyeme",
          "deuxieme_temoin_nom": "MBALLA Etienne",
          "deuxieme_temoin_profession": "Retraité",
          "deuxieme_temoin_residence": "Ebolowa",
          "officier_etat_civil": "OBAM Charles",
          "centre_etat_civil": "CEEB01"
      }'
     ```
3. **Upload a Document**:
   - Example:
     ```bash
     curl -X POST http://localhost:8000/documents -H "Authorization: Bearer <token>" -F "fichier=@document.jpg" -F "demande_id=1"
     ```
4. **Search a Request**:
   - Example:
     ```bash
     curl -X POST http://localhost:8000/search -H "Authorization: Bearer <token>" -d '{"type_demande": "birth_certificate", "numero_acte": "12345", "centre": "Centre"}'
     ```

### 🔗 Communication with Angara
1. **Exchange Public Keys**:
   - Retrieve Angara’s public key:
     ```bash
     curl http://angara:8000/keys/public-key
     ```
   - Set Angara’s public key in BUNEC:
     ```bash
     curl -X POST http://localhost:8000/keys/set-public-key -H "Authorization: Bearer <token>" -d '{"public_key": "<angara-public-key>"}'
     ```
2. **Send/Receive Encrypted Requests**:
   - Send to Angara:
     ```bash
     curl -X POST http://localhost:8000/comm/send-request -H "Authorization: Bearer <token>" -d '{"request_id": 1, "request_type": "birth_certificate", "client_id": 123}'
     ```
   - Receive from Angara:
     ```bash
     curl -X POST http://localhost:8000/comm/receive-request -d '{"ciphertext": "<ciphertext>", "signature": "<signature>"}'
     ```

## 🧪 Testing

- **Unit Tests**:
  - Use `pytest` for testing services.
  - Example:
    ```bash
    pytest tests/
    ```
- **Integration Tests**:
  - Use Swagger UI (`http://localhost:8000/docs`) or `curl` for endpoint testing.
  - Example:
    ```bash
    curl -X GET http://localhost:8000/requests/1 -H "Authorization: Bearer <token>"
    ```

## 🛠️ Troubleshooting

- **Database Connection Issues**:
  - Verify `DATABASE_URL` in `.env` and ensure PostgreSQL is running.
  - Test: `psql -h localhost -U postgres -d bunec`
- **Authentication Errors**:
  - Ensure the JWT token is valid and includes the correct `client_id`.
  - Debug with `python-jose` logs.
- **Document Upload Issues**:
  - Ensure `src/static` exists and is writable.
  - Verify file type (JPEG/PNG) and size (<5MB).
- **Angara Communication Errors**:
  - Check RSA key exchange and validate public keys.
  - Ensure Angara’s endpoint is accessible.

## ⚡ Performance Considerations
- **Database**: Indexes on `numero_acte`, `nom_complet`, `ville`, etc., improve query performance.
- **Connection Pooling**: Configured in `db.py` with `pool_size=10`, `max_overflow=20`, and `pool_recycle=1800`.
- **File Storage**: Use cloud storage (e.g., AWS S3) for production to handle large volumes.
- **Scalability**: Deploy with a reverse proxy (e.g., Nginx) and multiple Uvicorn workers for high traffic.

## 🤝 Contributing
1. Fork the repository 🍴.
2. Create a branch: `git checkout -b feature/xyz` 🌿.
3. Commit changes: `git commit -m "Add feature xyz"` 📝.
4. Push branch: `git push origin feature/xyz` 🚀.
5. Open a pull request 📥.

## 📜 License
This project is licensed under the **MIT License**. See the `LICENSE` file for details.

## 📞 Contact
For questions or support, contact the development team at **nanyangbrice.devops@gmail.com** 📧 or open an issue on the repository.