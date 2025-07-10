# The Last Algorithm Backend - Server Setup Guide

## Quick Start (For WSL2/Linux)

### Prerequisites Check
1. **Virtual Environment**: Ensure `venv/` directory exists
2. **Dependencies**: Check if FastAPI, uvicorn, redis are installed
3. **Environment Variables**: Verify `.env` file has required keys

### Starting the Server

**Method 1: Background Process (Recommended)**
```bash
# Navigate to project directory
cd /mnt/c/Users/Yavor/Downloads/keeper/the-last-algorithm-backend

# Activate virtual environment
source venv/bin/activate

# Start server in background
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

**Method 2: Foreground Process (For Debugging)**
```bash
# Navigate to project directory
cd /mnt/c/Users/Yavor/Downloads/keeper/the-last-algorithm-backend

# Activate virtual environment
source venv/bin/activate

# Start server with live reload
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the Server

**From Browser (Windows):**
- Main API: `http://localhost:8000`
- Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

**From WSL/Linux:**
- Main API: `http://127.0.0.1:8000`
- Documentation: `http://127.0.0.1:8000/docs`

### Verifying Server is Running

**Check Process:**
```bash
ps aux | grep uvicorn
```

**Test API Response:**
```bash
curl http://localhost:8000
```

**Expected Response:**
```json
{
  "message": "The Last Algorithm Backend API",
  "status": "running", 
  "docs": "/docs"
}
```

### Common Issues & Solutions

#### Issue 1: Server Not Accessible from Browser
**Symptoms:** Browser shows "can't connect" or times out
**Cause:** WSL2 networking issues
**Solution:** 
- Ensure server uses `--host 0.0.0.0` (not 127.0.0.1)
- Try accessing via WSL IP: `http://172.21.186.144:8000`
- Use PowerShell port forwarding if needed

#### Issue 2: Server Stops After Starting
**Symptoms:** Server starts but then terminates
**Cause:** Async function calls without await
**Solution:** 
- Check all `get_redis_client()` calls have `await`
- Verify all async functions are properly awaited

#### Issue 3: Import Errors
**Symptoms:** Module not found errors
**Cause:** Missing dependencies or wrong directory
**Solution:**
- Ensure virtual environment is activated
- Install missing packages: `pip install -r requirements.txt`
- Verify working directory is correct

#### Issue 4: Redis Connection Issues
**Symptoms:** Redis connection timeouts
**Cause:** Invalid REDIS_URL in .env
**Solution:**
- Verify REDIS_URL format in `.env`
- Test Redis connection separately

### Environment Variables Required

Create `.env` file with:
```env
OPENAI_API_KEY=sk-proj-...
REDIS_URL=redis://default:password@host:port
PORT=8000
ENVIRONMENT=development
```

### Server Status Indicators

**✅ Server Running Successfully:**
- Process visible in `ps aux | grep uvicorn`
- HTTP 200 response from health endpoint
- FastAPI docs accessible at `/docs`

**❌ Server Not Running:**
- No uvicorn process found
- Connection refused errors
- No response from health endpoint

### Troubleshooting Commands

```bash
# Check server process
ps aux | grep uvicorn

# Check port usage
netstat -tlnp | grep :8000

# Test local connection
curl http://localhost:8000/health

# Check logs (if using nohup)
tail -f nohup.out

# Kill existing server
pkill -f uvicorn
```

### Development Workflow

1. **Start Development Server:**
   ```bash
   source venv/bin/activate
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Test Changes:**
   - Visit `http://localhost:8000/docs`
   - Use interactive API documentation
   - Test endpoints with curl or browser

3. **Stop Server:**
   - Press `Ctrl+C` in terminal
   - Or kill process: `pkill -f uvicorn`

### Production Deployment Notes

- Use `--workers` for multiple processes
- Set `--host 0.0.0.0` for external access
- Use process manager like supervisor or systemd
- Configure proper logging and monitoring

---

**Last Updated:** July 2025
**Server Version:** FastAPI 1.0.0
**Python Version:** 3.x required