# Auth Frontend

React/Vite client for the split auth and area project.

## Run

```bash
npm install
npm run dev
```

The auth API base URL is configured in `src/api/config.js`.

Default:

```js
http://127.0.0.1:8000/api/v1/auth
```

The client stores access and refresh tokens in local storage, refreshes expired
access tokens when possible, and sends the refresh token during logout so the
backend can close the current session.
