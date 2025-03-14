# IBEam Server for Atomik Trading

Interactive Brokers trading server that runs in a dedicated environment for each user.
This server provides a REST API for trading operations with IB accounts.

## Environment Variables
- `IB_USERNAME`: Interactive Brokers username
- `IB_PASSWORD`: Interactive Brokers password
- `API_KEY`: API key for securing the server
- `USER_ID`: User ID from the main application
- `ENVIRONMENT`: Deployment environment (production, development)