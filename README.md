# Fireguard Project

Fireguard is a project for finding the predicted fire-risk for a specific location within a specific timeframe.  
It utilizes a FastAPI backend, MongoDB for data storage, and Keycloak for authentication and authorization.


## Prerequisites

Before you begin, ensure you have the following installed:

- [Docker](https://www.docker.com/get-started/)
- [Docker Compose](https://docs.docker.com/compose/install/)


## Setup and Installation

### 1. Clone the Repository

```bash
git clone git@github.com:591358/fireguard-group-6.git
cd fireguard-group-6
```

---

### 2. Configuration

Before running the project, there are a few things you need to do:

- **Create a `.env` file:** Copy the example `.env` file and fill in the required credentials.

    ```bash
    cp example.env .env
    ```

- **Edit the `.env` file:** Modify the `.env` file with your specific configuration details.  
  Here's a breakdown of the required variables:

    ```env
    # --- External API Credentials (e.g., MET API) ---
    MET_CLIENT_ID=your-met-client-id
    MET_CLIENT_SECRET=your-met-client-secret

    # --- MongoDB Credentials and URI ---
    MONGO_USER=your-mongo-username
    MONGO_PASSWORD=your-mongo-password
    MONGO_URI=mongodb://your-mongo-username:your-mongo-password@mongo:27017/fireguard

    # --- Keycloak Authentication Configuration ---
    KEYCLOAK_URL=http://localhost:8080
    REALM_NAME=your-realm-name

    # --- Client Credentials for Application ---
    CLIENT_ID=your-client-id
    CLIENT_SECRET=your-client-secret

    # --- Admin Client Credentials for Management Access ---
    ADMIN_CLIENT_ID=admin-client-id
    ADMIN_CLIENT_SECRET=admin-client-secret

    # --- JWT Configuration ---
    ALGORITHM=RS256

    # --- Keycloak Admin User (used to fetch tokens programmatically) ---
    KEYCLOAK_ADMIN=admin
    KEYCLOAK_ADMIN_PASSWORD=admin
    ```

    **Important Notes:**
    - Replace all `your-...` placeholders with your actual values.
    - **Keycloak Setup is Required:** You must have a running Keycloak instance configured with a realm and appropriate clients. See the [Keycloak Configuration](#keycloak-configuration) section for details.

---

### 3. Start the Services

```bash
docker compose up -d
docker-compose up --build
```

This will build the FastAPI image and start all services defined in the `compose.yaml` file (FastAPI, MongoDB, and Keycloak).


## Keycloak Configuration

After Keycloak is running at [http://localhost:8080](http://localhost:8080), perform the following steps:


### 1. Accessing Keycloak Admin Console

Open your web browser and navigate to `http://localhost:8080`.  
Log in using the credentials defined by the `KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD` variables in your `.env` file.


### 2. Creating a Realm

If you don't already have one, create a new realm.  
The realm name should match the `REALM_NAME` in your `.env` file.


### 3. Creating Clients

You’ll need to create at least **two clients** within your realm:

#### Application Client

This client is used by your FastAPI application to authenticate users.

- **Client ID:** Set to the value of `CLIENT_ID` in your `.env` file.
- **Access Type:** Set to `confidential` and provide a secret.  
  The secret should match the `CLIENT_SECRET` in your `.env` file.
- **Service Accounts Enabled:** Enable this setting to allow backend access and the `Client Credentials` grant type.

![Application Client Configuration](image.png)


#### Admin Client

This client is used for administrative tasks (e.g., programmatically fetching tokens).

- **Client ID:** Set to the value of `ADMIN_CLIENT_ID` (or use `admin-cli`) in your `.env` file.
- **Access Type:** Set to `confidential` and provide a secret.  
  Either use the one you configure, or find the current one in the credentials tab.  
  The secret should match the `ADMIN_CLIENT_SECRET` in your `.env` file.
- **Service Accounts Enabled:** Enable this setting to allow backend access and the `Client Credentials` grant type.

![Admin Client Configuration](image-1.png)


#### Service Account Roles

- Assign **all roles** under Service Account Roles (do this for both clients just to be sure).

![Service Account Roles Assignment](image-3.png)


### 4. User Setup

Create users within your realm who will be able to access your application.

## Creating a New User

The application provides an endpoint for creating new users, which handles the creation in both Keycloak and the MongoDB database.  
This process requires administrative privileges.

**Endpoint:** `POST /users/`

Example:

```bash
POST http://localhost:8000/users/

# Example payload
{
  "username": "test_user",
  "email": "test_user@example.com",
  "password": "Test1234!"
}
```


## Usage

Once the services are running, you can access the FastAPI application at [http://localhost:8000](http://localhost:8000).

- **API Documentation:**  
  Access the automatically generated Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs). 

---

## Obtaining an Access Token

To authenticate and access secured endpoints, you need to obtain an **access token** from Keycloak.

### Request Details

**Endpoint:**  
`POST http://localhost:8080/realms/your-realm/protocol/openid-connect/token`

**Headers:**  
- `Content-Type: application/x-www-form-urlencoded`

**Body Parameters (x-www-form-urlencoded):**

| Key           | Value                        | Description                        |
| -------------- | ----------------------------- | ---------------------------------- |
| `client_id`    | Your client ID                | Application client ID from `.env`  |
| `client_secret`| Your client secret            | Application client secret from `.env` |
| `username`     | Your username                 | Username of the user logging in    |
| `password`     | Your password                 | Password of the user logging in    |
| `grant_type`   | `password`                    | Type of grant to request a token   |
| `scope`        | `openid`                      | Scope of authentication            |

### Example (using `curl`)

```bash
curl --request POST \
  --url http://localhost:8080/realms/your-realm/protocol/openid-connect/token \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'client_id=your-client-id' \
  --data-urlencode 'client_secret=your-client-secret' \
  --data-urlencode 'username=your-username' \
  --data-urlencode 'password=your-password' \
  --data-urlencode 'grant_type=password' \
  --data-urlencode 'scope=openid'
```

**Response Example:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "not-before-policy": 0,
  "session_state": "abc123",
  "scope": "openid email profile"
}
```

Once you have the `access_token`, you can include it in the `Authorization` header when making authenticated requests to your FastAPI backend:

```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```


**Important:**  

- Tokens typically expire after a short time (e.g., 5 minutes), so be prepared to refresh the token if needed.


## Running Tests

To run the tests, execute the following command:

```bash
docker compose run fastapi-test
```

This will execute the `pytest` command defined in the `compose.yaml` file.

