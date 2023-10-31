# Hello Fast API

```sh
uvicorn main:app --reload
```

- `main`: the file main.py (the Python "module").
- `app`: the object created inside of main.py with the line `app = FastAPI()`.
- `--reload`: make the server restart after code changes. Only use for development.

## Docs

Automatically generated docs by Swagger UI at:

```sh
http://127.0.0.1:8000/docs
```
