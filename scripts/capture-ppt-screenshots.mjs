import { spawn, execFileSync } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const backendDir = path.join(root, 'backend')
const frontendDir = path.join(root, 'frontend')
const outputDir = path.join(root, 'docs', 'ppt-images')
const backendUrl = 'http://127.0.0.1:8000'
const frontendUrl = 'http://127.0.0.1:5173'
const python = path.join(backendDir, 'venv', 'Scripts', 'python.exe')
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'

const chromeCandidates = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
]

const viewport = { width: 1440, height: 900 }
const started = []
const servers = []

function log(message) {
  console.log(`[capture] ${message}`)
}

function exists(filePath) {
  return fs.existsSync(filePath)
}

async function waitForUrl(url, timeoutMs = 30000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const resp = await fetch(url)
      if (resp.ok) return true
    } catch {}
    await delay(500)
  }
  return false
}

function startProcess(command, args, cwd, logName) {
  const out = fs.openSync(path.join(outputDir, `${logName}.out.log`), 'w')
  const err = fs.openSync(path.join(outputDir, `${logName}.err.log`), 'w')
  const child = spawn(command, args, {
    cwd,
    stdio: ['ignore', out, err],
    windowsHide: true,
    shell: process.platform === 'win32' && command.toLowerCase().endsWith('.cmd'),
  })
  started.push(child)
  return child
}

function runBackendCommand(args) {
  execFileSync(python, args, {
    cwd: backendDir,
    stdio: 'inherit',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  })
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  return {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.json': 'application/json; charset=utf-8',
  }[ext] || 'application/octet-stream'
}

async function readRequestBody(req) {
  const chunks = []
  for await (const chunk of req) chunks.push(chunk)
  return Buffer.concat(chunks)
}

async function startStaticFrontend() {
  const distDir = path.join(frontendDir, 'dist')
  const indexPath = path.join(distDir, 'index.html')
  if (!exists(indexPath)) {
    log('未找到 frontend/dist，先执行前端构建')
    execFileSync(npmCmd, ['run', 'build'], {
      cwd: frontendDir,
      stdio: 'inherit',
      shell: process.platform === 'win32',
    })
  }

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url || '/', frontendUrl)
      if (url.pathname.startsWith('/api/')) {
        const body = ['GET', 'HEAD'].includes(req.method || '') ? undefined : await readRequestBody(req)
        const headers = { ...req.headers }
        delete headers.host
        const upstream = await fetch(`${backendUrl}${url.pathname}${url.search}`, {
          method: req.method,
          headers,
          body,
        })
        res.writeHead(upstream.status, Object.fromEntries(upstream.headers.entries()))
        if (upstream.body) {
          const buffer = Buffer.from(await upstream.arrayBuffer())
          res.end(buffer)
        } else {
          res.end()
        }
        return
      }

      let filePath = path.normalize(path.join(distDir, decodeURIComponent(url.pathname)))
      if (!filePath.startsWith(distDir)) {
        res.writeHead(403)
        res.end('Forbidden')
        return
      }
      if (!path.extname(filePath) || !exists(filePath)) filePath = indexPath
      res.writeHead(200, { 'content-type': contentType(filePath) })
      fs.createReadStream(filePath).pipe(res)
    } catch (err) {
      res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
      res.end(String(err?.stack || err))
    }
  })

  await new Promise((resolve, reject) => {
    server.listen(5173, '127.0.0.1', resolve)
    server.on('error', reject)
  })
  servers.push(server)
}

async function ensureServers() {
  if (!exists(python)) {
    throw new Error(`未找到后端虚拟环境 Python：${python}`)
  }

  fs.mkdirSync(outputDir, { recursive: true })

  log('检查数据库迁移和演示账号')
  runBackendCommand(['manage.py', 'migrate', '--noinput'])
  runBackendCommand([
    'manage.py',
    'shell',
    '-c',
    "from django.contrib.auth import get_user_model; U=get_user_model(); u,_=U.objects.get_or_create(username='admin', defaults={'role':'admin','is_staff':True,'is_superuser':True,'email':'admin@sleep-system.example'}); u.role='admin'; u.is_staff=True; u.is_superuser=True; u.set_password('admin123'); u.save(); print('admin/admin123 ready')",
  ])

  if (!(await waitForUrl(`${backendUrl}/api/healthz/`, 1000))) {
    log('启动 Django 后端')
    startProcess(python, ['manage.py', 'runserver', '127.0.0.1:8000', '--noreload'], backendDir, 'backend')
    if (!(await waitForUrl(`${backendUrl}/api/healthz/`, 30000))) {
      throw new Error('Django 后端未能在 30 秒内启动')
    }
  } else {
    log('复用已运行的 Django 后端')
  }

  if (!(await waitForUrl(frontendUrl, 1000))) {
    log('启动静态前端服务')
    await startStaticFrontend()
    if (!(await waitForUrl(frontendUrl, 30000))) {
      throw new Error('静态前端服务未能在 30 秒内启动')
    }
  } else {
    log('复用已运行的前端服务')
  }
}

async function apiLogin(username, password) {
  const resp = await fetch(`${backendUrl}/api/auth/login/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!resp.ok) {
    throw new Error(`${username} 登录失败：${resp.status} ${await resp.text()}`)
  }
  return resp.json()
}

async function ensureDemoData() {
  try {
    await apiLogin('student01', 'student123')
    await apiLogin('teacher01', 'teacher123')
    await apiLogin('parent01', 'parent123')
    log('演示账号已存在')
  } catch {
    log('演示账号不存在，生成种子数据')
    runBackendCommand(['manage.py', 'seed_demo_data', '--yes'])
  }
}

async function makeStudentAdvice(session) {
  const resp = await fetch(`${backendUrl}/api/ai/advice/`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${session.access}`,
    },
  })
  if (!resp.ok && resp.status !== 429) {
    log(`AI 建议预生成跳过：${resp.status}`)
  }
}

function findChrome() {
  const found = chromeCandidates.find(exists)
  if (!found) {
    throw new Error('未找到 Chrome/Edge，可安装 Chrome 后重试')
  }
  return found
}

async function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl
    this.nextId = 1
    this.pending = new Map()
    this.events = new Map()
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl)
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true })
      this.ws.addEventListener('error', reject, { once: true })
    })
    this.ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
        return
      }
      if (msg.method && this.events.has(msg.method)) {
        for (const fn of this.events.get(msg.method)) fn(msg.params)
      }
    })
  }

  send(method, params = {}) {
    const id = this.nextId++
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
    })
  }

  once(method, timeoutMs = 10000) {
    return new Promise((resolve) => {
      const handlers = this.events.get(method) || new Set()
      let timer = null
      const fn = (params) => {
        clearTimeout(timer)
        handlers.delete(fn)
        resolve(params)
      }
      handlers.add(fn)
      this.events.set(method, handlers)
      timer = setTimeout(() => {
        handlers.delete(fn)
        resolve(null)
      }, timeoutMs)
    })
  }

  close() {
    try { this.ws.close() } catch {}
  }
}

async function launchBrowser() {
  const chrome = findChrome()
  const port = await freePort()
  const userDataDir = path.join(outputDir, '.chrome-profile')
  fs.rmSync(userDataDir, { recursive: true, force: true })
  fs.mkdirSync(userDataDir, { recursive: true })

  log(`启动浏览器：${path.basename(chrome)}`)
  const child = spawn(chrome, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    `--window-size=${viewport.width},${viewport.height}`,
    'about:blank',
  ], { stdio: 'ignore', windowsHide: true })
  started.push(child)

  const versionUrl = `http://127.0.0.1:${port}/json/version`
  if (!(await waitForUrl(versionUrl, 15000))) {
    throw new Error('浏览器调试端口未启动')
  }
  const target = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' }).then(r => r.json())
  const cdp = new CdpClient(target.webSocketDebuggerUrl)
  await cdp.connect()
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Network.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: false,
  })
  return cdp
}

async function navigate(cdp, url, settleMs = 1600) {
  const loaded = cdp.once('Page.loadEventFired', 12000)
  await cdp.send('Page.navigate', { url })
  await loaded
  await delay(settleMs)
}

async function setSession(cdp, session) {
  await navigate(cdp, `${frontendUrl}/login`, 500)
  const expression = `
    localStorage.clear();
    localStorage.setItem('access_token', ${JSON.stringify(session.access)});
    localStorage.setItem('refresh_token', ${JSON.stringify(session.refresh)});
    localStorage.setItem('user', ${JSON.stringify(JSON.stringify(session.user))});
  `
  await cdp.send('Runtime.evaluate', { expression })
}

async function screenshot(cdp, filename) {
  const data = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  })
  fs.writeFileSync(path.join(outputDir, filename), Buffer.from(data.data, 'base64'))
  log(`已保存 ${filename}`)
}

function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function slideHtml(title, body) {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      width: 1440px;
      height: 900px;
      overflow: hidden;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: #f4f7fb;
      color: #172033;
    }
    .slide {
      width: 1440px;
      height: 900px;
      padding: 54px 70px;
      background:
        linear-gradient(135deg, rgba(31, 111, 235, .08), rgba(22, 163, 139, .08)),
        #f8fafc;
    }
    h1 { margin: 0 0 28px; font-size: 38px; letter-spacing: 0; color: #10233f; }
    h2 { margin: 0 0 14px; font-size: 24px; color: #183b64; }
    .subtitle { color: #607086; font-size: 18px; margin-top: -16px; margin-bottom: 28px; }
    .grid { display: grid; gap: 18px; }
    .cols-2 { grid-template-columns: repeat(2, 1fr); }
    .cols-3 { grid-template-columns: repeat(3, 1fr); }
    .cols-4 { grid-template-columns: repeat(4, 1fr); }
    .card {
      background: rgba(255,255,255,.94);
      border: 1px solid #dbe5f0;
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 12px 28px rgba(25, 47, 75, .08);
    }
    .chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 9px 14px;
      border-radius: 999px;
      background: #eef6ff;
      color: #1f5fae;
      border: 1px solid #cfe2ff;
      font-weight: 700;
      margin: 5px;
    }
    .box {
      border: 2px solid #96b8df;
      background: #ffffff;
      border-radius: 12px;
      padding: 16px 18px;
      text-align: center;
      min-height: 78px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: 5px;
    }
    .box strong { font-size: 20px; color: #143c66; }
    .box span { font-size: 13px; color: #66758b; }
    .arrow { text-align: center; color: #3b82f6; font-size: 26px; font-weight: 700; }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 12px 28px rgba(25,47,75,.08);
      font-size: 18px;
    }
    th { background: #eaf3ff; color: #163b66; }
    th, td { border: 1px solid #d9e5f2; padding: 14px 16px; text-align: left; }
    td.center, th.center { text-align: center; }
    .ok { color: #15803d; font-weight: 700; }
    .warn { color: #b45309; font-weight: 700; }
    .deny { color: #b91c1c; font-weight: 700; }
    .metric {
      font-size: 56px;
      font-weight: 800;
      color: #0f766e;
      line-height: 1;
    }
    .metric-label { margin-top: 10px; color: #5d6c80; font-size: 18px; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      line-height: 1.55;
      font-family: Consolas, "Cascadia Code", monospace;
      font-size: 17px;
      background: #0f172a;
      color: #dbeafe;
      padding: 22px;
      border-radius: 14px;
      box-shadow: 0 16px 36px rgba(15, 23, 42, .24);
    }
    .terminal { background:#101826; color:#d1fae5; }
    .small { font-size: 15px; color: #68778b; line-height: 1.7; }
    .line { height: 2px; background: #bfd2e8; margin: 16px 0; }
    ul { margin: 8px 0 0 20px; padding: 0; line-height: 1.75; font-size: 18px; }
    .badge { display:inline-block; padding: 6px 10px; border-radius: 8px; background:#dcfce7; color:#166534; font-weight:700; margin-right:8px; }
    .flow { display:grid; grid-template-columns: 1fr 42px 1fr 42px 1fr 42px 1fr; align-items:center; gap:10px; }
  </style>
</head>
<body><div class="slide"><h1>${esc(title)}</h1>${body}</div></body>
</html>`
}

async function captureHtml(cdp, filename, title, body, wait = 800) {
  const html = slideHtml(title, body)
  await navigate(cdp, `data:text/html;charset=utf-8,${encodeURIComponent(html)}`, wait)
  await screenshot(cdp, filename)
}

function scoreEngineSnippet() {
  return `def compute_score(
    bedtime: datetime,
    wake_time: datetime,
    subjective: int = 3,
) -> ScoreResult:
    if wake_time <= bedtime:
        raise ValueError("wake_time 必须晚于 bedtime")

    duration_minutes = int((wake_time - bedtime).total_seconds() // 60)
    belong_date = _belongs_to_date(bedtime)

    ds = _compute_duration_score(duration_minutes)   # 50%
    bs = _compute_bedtime_score(bedtime, belong_date) # 30%
    ss = _compute_subjective_score(subjective)        # 20%

    quality = ds + bs + ss
    status = _status_from_quality(quality)

    return ScoreResult(
        date=belong_date,
        duration_minutes=duration_minutes,
        quality_score=quality,
        status=status,
        is_weekend_night=_is_weekend_night(belong_date),
    )`
}

async function captureDiagrams(cdp) {
  const code = esc(scoreEngineSnippet())
  const testText = esc(`$ python -m pytest tests/test_score_engine.py -q
............                                                             [100%]
12 passed in 0.02s

后端冒烟链路：
✅ 注册 / 登录 / 班级邀请码 / 家长邀请码
✅ 打卡 / 跨天归属 / 补卡 / 老师代改审计
✅ 前端 production build 通过`)

  await captureHtml(cdp, '13-background-chart.png', '研究背景与选题意义', `
    <div class="grid cols-2" style="align-items:stretch">
      <div class="card">
        <h2>教育场景睡眠目标</h2>
        <div style="height:420px; display:flex; align-items:end; gap:48px; padding:20px 32px 0">
          ${[['小学',10,'#0ea5e9'],['初中',9,'#14b8a6'],['高中',8,'#f59e0b']].map(([name,h,color]) => `
            <div style="flex:1; text-align:center">
              <div style="height:${Number(h) * 34}px; background:${color}; border-radius:14px 14px 0 0; box-shadow:0 12px 24px rgba(0,0,0,.12)"></div>
              <div style="font-size:42px; font-weight:800; color:${color}; margin-top:12px">${h}h</div>
              <div style="font-size:20px; color:#475569">${name}</div>
            </div>`).join('')}
        </div>
      </div>
      <div class="card">
        <h2>项目切入点</h2>
        <ul>
          <li>现有睡眠工具多面向成年人，缺少校园班级管理场景。</li>
          <li>中学生睡眠管理需要学生、老师、家长形成闭环。</li>
          <li>系统将睡眠记录、评分、预警、AI 建议和报表导出串联起来。</li>
        </ul>
        <div class="line"></div>
        <div class="grid cols-3">
          <div class="box"><strong>学生</strong><span>低负担打卡</span></div>
          <div class="box"><strong>老师</strong><span>班级监督</span></div>
          <div class="box"><strong>家长</strong><span>异常关注</span></div>
        </div>
      </div>
    </div>`)

  await captureHtml(cdp, '14-role-painpoints.png', '角色与痛点分析', `
    <div class="grid cols-4">
      <div class="card"><h2>学生</h2><ul><li>想记录但嫌麻烦</li><li>担心日记隐私泄露</li><li>希望看到可理解反馈</li></ul></div>
      <div class="card"><h2>老师</h2><ul><li>缺少班级睡眠管理工具</li><li>无法快速定位异常学生</li><li>需要导出工作报告</li></ul></div>
      <div class="card"><h2>家长</h2><ul><li>缺少及时了解渠道</li><li>只关心异常和趋势</li><li>需要家校沟通入口</li></ul></div>
      <div class="card"><h2>管理员</h2><ul><li>账号和内容运维</li><li>演示数据初始化</li><li>全局统计监控</li></ul></div>
    </div>
    <div class="card" style="margin-top:22px">
      <h2>归纳：从“单人记录”升级为“三方协同”</h2>
      <div class="flow">
        <div class="box"><strong>学生打卡</strong><span>起床后回顾</span></div><div class="arrow">→</div>
        <div class="box"><strong>系统评分</strong><span>纯函数规则</span></div><div class="arrow">→</div>
        <div class="box"><strong>异常预警</strong><span>老师/家长触达</span></div><div class="arrow">→</div>
        <div class="box"><strong>持续干预</strong><span>AI 建议 + 报表</span></div>
      </div>
    </div>`)

  await captureHtml(cdp, '15-use-case-map.png', '核心用例图', `
    <div class="card" style="height:700px; position:relative">
      <div class="box" style="position:absolute; left:520px; top:260px; width:260px; height:120px; background:#eff6ff"><strong>学生睡眠管理系统</strong><span>Django REST + Vue SPA</span></div>
      <div style="position:absolute; left:45px; top:55px"><h2>学生</h2><span class="chip">睡眠打卡</span><span class="chip">历史记录</span><span class="chip">AI 建议</span><span class="chip">成就徽章</span></div>
      <div style="position:absolute; right:45px; top:55px; text-align:right"><h2>老师</h2><span class="chip">班级概览</span><span class="chip">预警中心</span><span class="chip">学生档案</span><span class="chip">报表导出</span></div>
      <div style="position:absolute; left:45px; bottom:60px"><h2>家长</h2><span class="chip">孩子概览</span><span class="chip">异常提醒</span><span class="chip">消息中心</span></div>
      <div style="position:absolute; right:45px; bottom:60px; text-align:right"><h2>管理员</h2><span class="chip">用户管理</span><span class="chip">文章管理</span><span class="chip">演示数据</span><span class="chip">全局统计</span></div>
      <svg width="1290" height="640" style="position:absolute; left:0; top:40px; pointer-events:none">
        <defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#60a5fa"/></marker></defs>
        <line x1="300" y1="120" x2="520" y2="285" stroke="#60a5fa" stroke-width="3" marker-end="url(#a)"/>
        <line x1="980" y1="120" x2="780" y2="285" stroke="#60a5fa" stroke-width="3" marker-end="url(#a)"/>
        <line x1="280" y1="520" x2="520" y2="355" stroke="#60a5fa" stroke-width="3" marker-end="url(#a)"/>
        <line x1="1000" y1="520" x2="780" y2="355" stroke="#60a5fa" stroke-width="3" marker-end="url(#a)"/>
      </svg>
    </div>`)

  await captureHtml(cdp, '16-architecture.png', '系统架构设计', `
    <div class="grid" style="grid-template-columns: 1fr 60px 1fr 60px 1fr">
      <div class="card"><h2>前端表现层</h2><div class="box"><strong>Vue 3 SPA</strong><span>Element Plus / Pinia / Router</span></div><div class="box" style="margin-top:14px"><strong>ECharts</strong><span>热力图 / 柱状图 / 饼图</span></div></div>
      <div class="arrow">↔</div>
      <div class="card"><h2>后端服务层</h2><div class="box"><strong>Django REST Framework</strong><span>JWT 鉴权 / 角色权限 / REST API</span></div><div class="box" style="margin-top:14px"><strong>业务模块</strong><span>sleep / users / notifications / ai</span></div></div>
      <div class="arrow">↔</div>
      <div class="card"><h2>数据与外部服务</h2><div class="box"><strong>SQLite / MySQL</strong><span>ORM + migrations</span></div><div class="box" style="margin-top:14px"><strong>DeepSeek / APScheduler</strong><span>AI 建议 / 定时 missed</span></div></div>
    </div>
    <div class="card" style="margin-top:24px"><h2>横切关注</h2><span class="chip">SimpleJWT</span><span class="chip">CORS</span><span class="chip">权限边界</span><span class="chip">报表导出</span><span class="chip">Dockerfile</span><span class="chip">Mock 兜底</span></div>`)

  await captureHtml(cdp, '17-tech-selection.png', '技术选型理由', `
    <table>
      <tr><th>技术</th><th>选型理由</th><th>在本项目中的作用</th></tr>
      <tr><td>Django 4 + DRF</td><td>成熟稳定，适合快速实现权限、ORM 和后台能力</td><td>REST API、模型、迁移、权限控制</td></tr>
      <tr><td>Vue 3 + Element Plus</td><td>组件完整，适合本科毕设快速构建管理端页面</td><td>四角色工作台、表格、表单、弹窗</td></tr>
      <tr><td>SQLite → MySQL</td><td>开发便捷，生产可平滑切换</td><td>.env DATABASE_URL 控制数据库</td></tr>
      <tr><td>SimpleJWT</td><td>前后端分离通用方案</td><td>登录态、刷新 token、角色路由</td></tr>
      <tr><td>DeepSeek + Mock</td><td>真实 LLM 与离线兜底兼顾</td><td>答辩演示不依赖外部 Key</td></tr>
    </table>`)

  await captureHtml(cdp, '18-database-er.png', '数据库 ER 核心关系', `
    <div class="grid cols-3">
      <div class="card"><h2>User</h2><div class="small">id / username / role / email / phone</div></div>
      <div class="card"><h2>ClassRoom</h2><div class="small">id / name / invite_code / teacher</div></div>
      <div class="card"><h2>SleepRecord</h2><div class="small">student / date / bedtime / wake_time / score / status</div></div>
      <div class="card"><h2>StudentProfile</h2><div class="small">student_no / real_name / classroom / target_sleep_hours</div></div>
      <div class="card"><h2>TeacherProfile</h2><div class="small">teacher_no / real_name</div></div>
      <div class="card"><h2>ParentProfile</h2><div class="small">real_name / child</div></div>
      <div class="card"><h2>Notification</h2><div class="small">recipient / title / type / read_at</div></div>
      <div class="card"><h2>AIAdvice</h2><div class="small">student / advice_text / is_mock / created_at</div></div>
      <div class="card"><h2>Article / Achievement</h2><div class="small">科普内容 / 成就解锁记录</div></div>
    </div>
    <div class="card" style="margin-top:20px">
      <span class="chip">User 1:1 Profile</span><span class="chip">ClassRoom 1:N StudentProfile</span><span class="chip">StudentProfile 1:N SleepRecord</span><span class="chip">SleepRecord unique(student,date)</span>
    </div>`)

  await captureHtml(cdp, '19-code-structure.png', '分层代码结构', `
    <div class="grid cols-2">
      <div class="card"><h2>后端 backend/</h2><pre>apps/
  users/          # 角色、注册、权限
  sleep/          # 打卡、统计、导出
  notifications/  # 预警与消息
  ai/             # DeepSeek + Mock
  achievements/   # 成就系统
  articles/       # 科普文章
utils/
  score_engine.py # 纯函数评分
  seed_data.py    # 10000+ 种子数据
  exporters.py    # Excel/PDF</pre></div>
      <div class="card"><h2>前端 frontend/src/</h2><pre>views/
  student/ teacher/ parent/ admin/
layouts/          # 四角色布局
stores/           # Pinia 登录态/通知
api/              # Axios API 封装
router/           # 角色路由守卫
style.css         # 全局视觉样式</pre>
      <div class="line"></div><div class="badge">设计重点</div><span class="small">业务规则集中、页面按角色分组、API 与 UI 解耦。</span></div>
    </div>`)

  await captureHtml(cdp, '20-score-engine-code.png', '评分引擎：纯函数与可测试性', `
    <div class="grid cols-2">
      <div class="card"><h2>评分模型</h2>
        <div class="metric">100</div><div class="metric-label">质量分满分</div>
        <div class="line"></div>
        <span class="chip">时长 50%</span><span class="chip">入睡时间 30%</span><span class="chip">主观分 20%</span>
        <ul><li>跨天归属：凌晨 0-4 点归前一晚</li><li>周五/周六晚健康线放宽到 00:00</li><li>状态分档：normal / warning / abnormal / severe</li></ul>
      </div>
      <pre>${code}</pre>
    </div>`, 1000)

  await captureHtml(cdp, '21-privacy-matrix.png', '三层隐私边界设计', `
    <table>
      <tr><th>数据/能力</th><th class="center">学生</th><th class="center">老师</th><th class="center">家长</th><th class="center">管理员</th></tr>
      <tr><td>睡眠打卡记录</td><td class="center ok">本人读写</td><td class="center ok">班级可读</td><td class="center ok">孩子可读</td><td class="center ok">运维可见</td></tr>
      <tr><td>睡眠日记</td><td class="center ok">默认私有</td><td class="center warn">授权后可见</td><td class="center deny">不可见</td><td class="center warn">非核心入口</td></tr>
      <tr><td>班级排行</td><td class="center warn">匿名同学A/B</td><td class="center ok">实名管理</td><td class="center deny">不可见</td><td class="center deny">不可见</td></tr>
      <tr><td>AI 建议</td><td class="center ok">个人私有</td><td class="center warn">班级整体诊断</td><td class="center deny">不可见</td><td class="center deny">不可见</td></tr>
      <tr><td>老师代改</td><td class="center warn">可查看结果</td><td class="center ok">需填写原因</td><td class="center warn">关注异常</td><td class="center ok">审计字段</td></tr>
    </table>`)

  await captureHtml(cdp, '22-ai-flow.png', 'AI 智能建议：真实调用 + Mock 兜底', `
    <div class="flow" style="margin-top:70px">
      <div class="box"><strong>近 7 天睡眠数据</strong><span>质量分 / 时长 / 最晚入睡 / 连续天数</span></div><div class="arrow">→</div>
      <div class="box"><strong>Prompt 构造</strong><span>面向中学生的中文建议</span></div><div class="arrow">→</div>
      <div class="box"><strong>DeepSeek Chat API</strong><span>有 Key 时真实调用</span></div><div class="arrow">→</div>
      <div class="box"><strong>建议入库</strong><span>AIAdvice 最近 30 条</span></div>
    </div>
    <div class="card" style="margin-top:36px">
      <h2>容错与限制</h2>
      <span class="chip">无 Key 自动 Mock</span><span class="chip">每人每天 3 次</span><span class="chip">老师仅班级整体诊断</span><span class="chip">不暴露个人日记</span>
    </div>`)

  await captureHtml(cdp, '23-engineering-metrics.png', '工程量化数据', `
    <div class="grid cols-4">
      <div class="card"><div class="metric">40+</div><div class="metric-label">前端页面/组件</div></div>
      <div class="card"><div class="metric">50+</div><div class="metric-label">RESTful API</div></div>
      <div class="card"><div class="metric">10000+</div><div class="metric-label">睡眠种子记录</div></div>
      <div class="card"><div class="metric">12</div><div class="metric-label">评分单元测试</div></div>
    </div>
    <div class="grid cols-3" style="margin-top:24px">
      <div class="card"><h2>数据规模</h2><ul><li>30 名学生</li><li>365 天历史</li><li>3 个典型案例</li></ul></div>
      <div class="card"><h2>工程能力</h2><ul><li>Dockerfile</li><li>一键运行脚本</li><li>SQLite/MySQL 切换</li></ul></div>
      <div class="card"><h2>业务闭环</h2><ul><li>打卡评分</li><li>异常预警</li><li>AI 建议</li><li>报表导出</li></ul></div>
    </div>`)

  await captureHtml(cdp, '24-test-validation.png', '测试与质量保障', `
    <div class="grid cols-2">
      <pre class="terminal">${testText}</pre>
      <div class="card"><h2>覆盖重点</h2>
        <ul>
          <li>跨天归属：凌晨入睡归前一晚。</li>
          <li>边界值：23:30 / 23:31 评分差异。</li>
          <li>周末放宽：周五、周六晚阈值不同。</li>
          <li>业务链路：注册、邀请码、打卡、补卡、代改审计。</li>
        </ul>
        <div class="line"></div>
        <span class="badge">结论</span><span class="small">核心规则可自动化验证，演示链路已跑通。</span>
      </div>
    </div>`)
}

async function capturePage(cdp, item, sessions) {
  if (item.role) await setSession(cdp, sessions[item.role])
  else {
    await navigate(cdp, `${frontendUrl}/login`, 500)
    await cdp.send('Runtime.evaluate', { expression: 'localStorage.clear()' })
  }
  await navigate(cdp, `${frontendUrl}${item.path}`, item.wait ?? 1800)
  if (item.evaluate) {
    await cdp.send('Runtime.evaluate', { expression: item.evaluate })
    await delay(item.evaluateWait ?? 1600)
  }
  await screenshot(cdp, item.file)
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true })
  await ensureServers()
  await ensureDemoData()

  const sessions = {
    student: await apiLogin('student02', 'student123'),
    teacher: await apiLogin('teacher01', 'teacher123'),
    parent: await apiLogin('parent01', 'parent123'),
    admin: await apiLogin('admin', 'admin123'),
  }
  await makeStudentAdvice(sessions.student)

  const pages = [
    { file: '01-login.png', path: '/login', wait: 1200 },
    { file: '02-student-dashboard.png', role: 'student', path: '/student', wait: 2600 },
    { file: '03-student-checkin.png', role: 'student', path: '/student/checkin', wait: 1800 },
    {
      file: '04-student-heatmap.png',
      role: 'student',
      path: '/student/heatmap',
      wait: 2600,
      evaluate: "Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('‹'))?.click()",
      evaluateWait: 2200,
    },
    { file: '05-student-ai-advice.png', role: 'student', path: '/student/ai', wait: 2200 },
    { file: '06-teacher-dashboard.png', role: 'teacher', path: '/teacher', wait: 2600 },
    { file: '07-teacher-students.png', role: 'teacher', path: '/teacher/students', wait: 2200 },
    { file: '08-teacher-alerts.png', role: 'teacher', path: '/teacher/alerts', wait: 2200 },
    { file: '09-teacher-export.png', role: 'teacher', path: '/teacher/export', wait: 1800 },
    { file: '10-parent-dashboard.png', role: 'parent', path: '/parent', wait: 2200 },
    { file: '11-admin-dashboard.png', role: 'admin', path: '/admin', wait: 2000 },
    { file: '12-admin-users.png', role: 'admin', path: '/admin/users', wait: 2200 },
  ]

  const cdp = await launchBrowser()
  try {
    for (const page of pages) await capturePage(cdp, page, sessions)
    await captureDiagrams(cdp)
  } finally {
    cdp.close()
  }

  log(`完成，图片目录：${outputDir}`)
}

main()
  .catch((err) => {
    console.error(err)
    process.exitCode = 1
  })
  .finally(() => {
    for (const server of servers.reverse()) {
      try { server.close() } catch {}
    }
    for (const child of started.reverse()) {
      try {
        if (!child.killed) child.kill()
      } catch {}
    }
  })
