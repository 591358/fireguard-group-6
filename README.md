# Fireguard Group 6

## Running the Project
To run the project, follow these steps:

1. Install dependencies:
   ```sh
   poetry install  # Might not be necessary if already installed
   ```

2. Create a `.env` file in the `src` folder and add the required credentials as described [here](https://pypi.org/project/dynamic-frcm/).

3. Run the main script:
   ```sh
   py main.py
   ```

4. Navigate to the `backend` folder and start FastAPI:
   ```sh
   fastapi dev main.py
   ```
   This will start the FastAPI server, and you should see output similar to:
   
   ![alt text](images/image.png)

## Installed Packages
```sh
poetry init
poetry add dynamic-frcm
poetry add python-dotenv
pip install "fastapi[standard]"
pip install pytest httpx mongomock
```

---

# Creating a FastAPI Endpoint
FastAPI makes it easy to create and update endpoints. Below is a simplified guide.

###  Define Your API Route in `main.py`
```python
from fastapi import FastAPI, HTTPException, Depends
from pymongo.collection import Collection
from bson import ObjectId
from database import get_location_collection
from pydantic import BaseModel

app = FastAPI()

class UpdateLocationModel(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None

@app.put("/location/{location_id}")
async def update_location(location_id: str, data: UpdateLocationModel, collection: Collection = Depends(get_location_collection)):
    object_id = ObjectId(location_id)
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    result = collection.update_one({"_id": object_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")

    return {"message": "Location updated", "updated_fields": update_data}
```

###  Test with Swagger UI
Go to:
```
http://127.0.0.1:8000/docs
```

---

# Writing Tests for FastAPI Endpoints

### Create a Test in `test.py`

```python
import mongomock
from fastapi.testclient import TestClient
from backend.main import app, get_location_collection

@pytest.fixture
def client():
    mock_client = mongomock.MongoClient()
    app.dependency_overrides[get_location_collection] = lambda: mock_client.db.location_collection
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_update_location(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    test_location = {"_id": mongomock.ObjectId(), "name": "Old Name"}
    mock_collection.insert_one(test_location)
    location_id = str(test_location["_id"])
    response = client.put(f"/location/{location_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["updated_fields"]["name"] == "New Name"
```

### Run Tests
```sh
pytest -v
```

---

# 🛠️ Git Commands Cheat Sheet
Here are some useful Git commands:

- `git clone <repository_url>` → Clone a remote repository
- `git pull` → Fetch and merge changes from the remote repository
- `git push` → Push local commits to the remote repository
- `git add .` → Stage all modified files
- `git commit -m "<message>"` → Commit staged files with a message
- `git status` → View the state of your repository
- `git merge <branch_name>` → Merge another branch into the current one
- `git checkout -b <branch_name>` → Create a new branch and switch to it
- `git stash` → Temporarily save uncommitted changes


