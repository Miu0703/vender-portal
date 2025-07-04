import os
import pytest
from app import create_app
from app.models import PackingListRow

@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": "tests/uploads"
    })
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Create authenticated test client"""
    client.post("/login", data={
        "username": "vendor",
        "password": "password123"
    })
    return client

@pytest.fixture
def sample_excel(tmp_path):
    """Create sample Excel file"""
    import pandas as pd
    data = {
        "ItemNo": ["A001", "B002"],
        "Description": ["Item A", "Item B"],
        "Qty": [100, 200],
        "UnitPrice": [10.50, 20.75]
    }
    df = pd.DataFrame(data)
    filepath = tmp_path / "sample.xlsx"
    df.to_excel(filepath, index=False)
    return str(filepath)

def test_login_required(client):
    """Test redirect to login page when not authenticated"""
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_login_success(client):
    """Test successful login"""
    response = client.post("/login", data={
        "username": "vendor",
        "password": "password123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Upload Packing List" in response.data.decode('utf-8')

def test_login_failure(client):
    """Test login failure"""
    response = client.post("/login", data={
        "username": "wrong",
        "password": "wrong"
    }, follow_redirects=True)
    assert response.status_code == 200
    # Check if we're back on the login page (login failed)
    assert "Vendor Login" in response.data.decode('utf-8')
    assert "Username" in response.data.decode('utf-8')

def test_upload_success(auth_client, sample_excel):
    """Test successful file upload"""
    with open(sample_excel, "rb") as f:
        response = auth_client.post("/", data={
            "file": (f, "test.xlsx")
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "Successfully processed" in response.data.decode('utf-8')
    assert "A001" in response.data.decode('utf-8')
    assert "Item A" in response.data.decode('utf-8')

def test_upload_invalid_file(auth_client):
    """Test upload invalid file"""
    response = auth_client.post("/", data={
        "file": (b"invalid data", "test.txt")
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Check if we're back on the upload page (upload failed)
    assert "Upload Packing List" in response.data.decode('utf-8')
    assert "Select File" in response.data.decode('utf-8')

def test_upload_missing_file(auth_client):
    """Test missing file upload"""
    response = auth_client.post("/", follow_redirects=True)
    assert response.status_code == 200
    # Check if we're back on the upload page (no file provided)
    assert "Upload Packing List" in response.data.decode('utf-8')
    assert "Select File" in response.data.decode('utf-8')

def test_end_to_end_flow(auth_client, sample_excel):
    """Test complete flow: login -> upload -> parse -> validate"""
    # 1. Upload file
    with open(sample_excel, "rb") as f:
        response = auth_client.post("/", data={
            "file": (f, "test.xlsx")
        }, follow_redirects=True)
    
    # 2. Verify response
    assert response.status_code == 200
    assert "Successfully processed" in response.data.decode('utf-8')
    
    # 3. Check data
    assert "A001" in response.data.decode('utf-8')
    assert "Item A" in response.data.decode('utf-8')
    assert "100" in response.data.decode('utf-8')
    assert "10.50" in response.data.decode('utf-8')
    
    # 4. Check JSON output
    assert '"status": "success"' in response.data.decode('utf-8')
    assert '"total": 2' in response.data.decode('utf-8') 