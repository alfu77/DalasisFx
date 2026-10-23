# DalasisFX — Azure Cloud Deployment & CI/CD

DalasisFX is a Flask-based currency converter deployed on Microsoft Azure using Docker and Kubernetes. The application is packaged as a container image, stored in Azure Container Registry (ACR), and deployed to Azure Kubernetes Service (AKS). Traefik Ingress provides external HTTP access to the application.

## Deployment Architecture

```text
Developer
   |
   | Push code
   v
GitHub Repository
   |
   v
GitHub Actions
   |
   | Build Docker image
   v
Azure Container Registry
   |
   | Pull versioned image
   v
Azure Kubernetes Service
   |
   | Kubernetes Service
   v
Traefik Ingress
   |
   v
DalasisFX Application
```

## Technology Stack

| Component | Technology |
|---|---|
| Application | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Containerization | Docker |
| Container registry | Azure Container Registry |
| Container orchestration | Azure Kubernetes Service |
| CI/CD | GitHub Actions |
| Ingress routing | Traefik |
| Cloud platform | Microsoft Azure |

## How It Is Deployed

### 1. Containerization with Docker

The Flask application is packaged into a Docker image with its application code and dependencies. This provides a consistent runtime environment and avoids relying on a manually started local development server.

### 2. Image Storage in Azure Container Registry

The Docker image is published to a private Azure Container Registry:

`ghostacr77.azurecr.io/dalasisfx`

ACR serves as the image registry from which Kubernetes can retrieve application versions for deployment.

### 3. Deployment to Azure Kubernetes Service

The application runs in an AKS cluster as a Kubernetes Deployment. Kubernetes manages the application pods and provides a declarative way to update the running image.

The application is exposed internally through a `ClusterIP` Service, keeping it separate from the external entry point.

### 4. External Access Through Traefik Ingress

Traefik runs as the Ingress controller and receives external HTTP traffic through a public IP address. The Kubernetes Ingress resource routes requests to the appropriate Service.

This allows DalasisFX and the portfolio website to share the same external entry point instead of requiring a separate public LoadBalancer IP for each application.

### 5. Continuous Integration and Continuous Deployment

A dedicated GitHub Actions workflow is used for the DalasisFX repository. The intended release flow is:

1. A code change is pushed to GitHub.
2. GitHub Actions builds a new Docker image.
3. The image is tagged and pushed to ACR.
4. The workflow updates the `dalasisfx` Deployment in AKS.
5. Kubernetes performs the rollout, and the workflow checks whether it completes successfully.

The pipeline's final triggers, authentication method, and rollout verification depend on the committed workflow configuration.

## Key Kubernetes Resources

| Resource | Purpose |
|---|---|
| Deployment: `dalasisfx` | Manages the application pods and image updates |
| Service: `dalasisfx` | Provides internal access to the Flask application |
| Ingress: `ghost-apps-ingress` | Routes incoming HTTP requests |
| Traefik Service | Exposes the Ingress controller externally |

## Running Locally

Requirements: Python 3, pip, and Docker.

```bash
git clone https://github.com/alfu77/dalasisfx.git
cd dalasisfx
```

Run with Python:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Run with Docker:

```bash
docker build -t dalasisfx:local .
docker run --rm -p 5000:5000 dalasisfx:local
```

Open `http://localhost:5000` in your browser.



## Author

**Alfu Jawneh**

GitHub: [@alfu77](https://github.com/alfu77)