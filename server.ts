import express from 'express';
import { createServer as createViteServer } from 'vite';
import { execFile, spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

const app = express();
const port = 3000;

app.use(express.json());

// 1. Scenarios endpoint
app.post('/api/scenarios/run', (req, res) => {
  const scenarioName = req.body.scenario || 'predefined';
  execFile('python3', ['cli_runner.py', 'scenario', scenarioName], (error, stdout, stderr) => {
    if (error) {
      console.error('Scenario run error:', stderr || error.message);
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      const data = JSON.parse(stdout.trim());
      res.json(data);
    } catch (e: any) {
      res.status(500).json({ error: 'Failed to parse scenario output', raw: stdout });
    }
  });
});

// 2. Unit tests runner endpoint
app.get('/api/tests/run', (req, res) => {
  execFile('python3', ['cli_runner.py', 'test'], (error, stdout, stderr) => {
    if (error && !stdout) {
      console.error('Test run error:', stderr || error.message);
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      const data = JSON.parse(stdout.trim());
      res.json(data);
    } catch (e: any) {
      res.status(500).json({ error: 'Failed to parse test output', raw: stdout });
    }
  });
});

// 3. Code explorer endpoint
const ALLOWED_EXTS = ['.py', '.md', '.toml', '.json', '.txt'];
app.get('/api/code/tree', (req, res) => {
  const getFiles = (dir: string): any[] => {
    const list: any[] = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const ent of entries) {
      if (['node_modules', '.git', '__pycache__', 'dist', '.vite'].includes(ent.name)) continue;
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        const children = getFiles(full);
        if (children.length > 0) {
          list.push({ name: ent.name, path: full.replace(/^\.\/?/, ''), type: 'directory', children });
        }
      } else if (ALLOWED_EXTS.some(ext => ent.name.endsWith(ext))) {
        list.push({ name: ent.name, path: full.replace(/^\.\/?/, ''), type: 'file' });
      }
    }
    return list;
  };

  try {
    const tree = [
      { name: 'turnprog', path: 'turnprog', type: 'directory', children: getFiles('./turnprog') },
      { name: 'tests', path: 'tests', type: 'directory', children: getFiles('./tests') },
      { name: 'README.md', path: 'README.md', type: 'file' },
      { name: 'setup.py', path: 'setup.py', type: 'file' },
      { name: 'pyproject.toml', path: 'pyproject.toml', type: 'file' },
      { name: 'cli_runner.py', path: 'cli_runner.py', type: 'file' },
    ];
    res.json(tree);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/code/file', (req, res) => {
  const filePath = (req.query.path as string) || '';
  // Prevent directory traversal
  const safePath = path.normalize(filePath).replace(/^(\.\.[\/\\])+/, '');
  const absPath = path.join(process.cwd(), safePath);

  if (!absPath.startsWith(process.cwd()) || !fs.existsSync(absPath) || fs.statSync(absPath).isDirectory()) {
    return res.status(404).json({ error: 'File not found' });
  }

  try {
    const content = fs.readFileSync(absPath, 'utf-8');
    res.json({ path: safePath, content });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// 4. Export zip endpoint
app.get('/api/export/zip', (req, res) => {
  const pyProcess = spawn('python3', ['cli_runner.py', 'export_zip']);
  res.setHeader('Content-Type', 'application/zip');
  res.setHeader('Content-Disposition', 'attachment; filename="turnprog-python-library.zip"');
  pyProcess.stdout.pipe(res);
  pyProcess.stderr.on('data', (err) => console.error('Export error:', err.toString()));
});

// Setup Vite middleware in dev or static files in prod
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true, hmr: process.env.DISABLE_HMR !== 'true' },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static('dist'));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve('dist', 'index.html'));
    });
  }

  app.listen(port, '0.0.0.0', () => {
    console.log(`Server listening on port ${port}`);
  });
}

startServer();
