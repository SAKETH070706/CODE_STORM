import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');

test('index.html contains complete production SEO, favicon, and social metadata', () => {
  const htmlPath = path.join(frontendDir, 'index.html');
  const htmlContent = fs.readFileSync(htmlPath, 'utf8');

  assert.ok(htmlContent.includes('<link rel="icon" type="image/svg+xml" href="/favicon.svg" />'), 'Missing favicon link');
  assert.ok(htmlContent.includes('<link rel="apple-touch-icon" href="/favicon.svg" />'), 'Missing apple-touch-icon');
  assert.ok(htmlContent.includes('<link rel="manifest" href="/manifest.json" />'), 'Missing manifest link');
  assert.ok(htmlContent.includes('<meta name="description"'), 'Missing meta description');
  assert.ok(htmlContent.includes('<meta property="og:title"'), 'Missing OpenGraph title');
  assert.ok(htmlContent.includes('<meta name="twitter:card"'), 'Missing Twitter card');
  assert.ok(htmlContent.includes('<link rel="canonical"'), 'Missing canonical URL');
  assert.ok(htmlContent.includes('<meta name="theme-color" content="#07090e" />'), 'Missing theme-color meta');
});

test('public/manifest.json is valid and contains required PWA metadata', () => {
  const manifestPath = path.join(frontendDir, 'public', 'manifest.json');
  assert.ok(fs.existsSync(manifestPath), 'manifest.json does not exist');
  
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  assert.equal(manifest.name, 'CODE_STORM GenAI Intelligence Platform');
  assert.equal(manifest.short_name, 'CODE_STORM');
  assert.equal(manifest.theme_color, '#07090e');
  assert.ok(manifest.icons.length > 0, 'manifest.icons should have entries');
});

test('public/robots.txt and public/sitemap.xml exist and are well-formed', () => {
  const robotsPath = path.join(frontendDir, 'public', 'robots.txt');
  assert.ok(fs.existsSync(robotsPath), 'robots.txt does not exist');
  const robots = fs.readFileSync(robotsPath, 'utf8');
  assert.ok(robots.includes('User-agent: *'), 'robots.txt missing User-agent');
  assert.ok(robots.includes('Sitemap:'), 'robots.txt missing Sitemap reference');

  const sitemapPath = path.join(frontendDir, 'public', 'sitemap.xml');
  assert.ok(fs.existsSync(sitemapPath), 'sitemap.xml does not exist');
  const sitemap = fs.readFileSync(sitemapPath, 'utf8');
  assert.ok(sitemap.includes('<urlset'), 'sitemap.xml missing urlset');
  assert.ok(sitemap.includes('https://codestorm.ai/'), 'sitemap.xml missing base URL');
});

test('App.css enforces zero horizontal overflow and responsive breakpoints', () => {
  const cssPath = path.join(frontendDir, 'src', 'App.css');
  const css = fs.readFileSync(cssPath, 'utf8');

  assert.ok(css.includes('.table-responsive'), 'Missing table responsive wrapper');
  assert.ok(css.includes('@media (max-width: 640px)'), 'Missing mobile breakpoint in App.css');
  assert.ok(css.includes('@media (max-width: 768px)'), 'Missing tablet/mobile hamburger breakpoint in App.css');
  assert.ok(css.includes('.hamburger-btn'), 'Missing hamburger button CSS');
  assert.ok(css.includes('.mobile-menu-drawer'), 'Missing mobile drawer CSS');
  assert.ok(css.includes('.toast-container'), 'Missing toast container CSS');
});

test('Footer contains valid clickable contact links and dynamic copyright year', () => {
  const footerPath = path.join(frontendDir, 'src', 'components', 'Footer.jsx');
  const footerCode = fs.readFileSync(footerPath, 'utf8');

  assert.ok(footerCode.includes('href="mailto:support@codestorm.ai"'), 'Missing clickable mailto link');
  assert.ok(footerCode.includes('href="tel:+18005550199"'), 'Missing clickable tel link');
  assert.ok(footerCode.includes('href="/docs"'), 'Missing FastAPI Swagger link');
  assert.ok(footerCode.includes('href="/ready"'), 'Missing /ready status link');
  assert.ok(footerCode.includes('CURRENT_YEAR'), 'Missing dynamic year reference in footer');
});

test('Navbar has clickable brand button and accessible hamburger controls', () => {
  const navbarPath = path.join(frontendDir, 'src', 'components', 'Navbar.jsx');
  const navbarCode = fs.readFileSync(navbarPath, 'utf8');

  assert.ok(navbarCode.includes('className="brand-btn"'), 'Brand logo should be an interactive button');
  assert.ok(navbarCode.includes('aria-label="Toggle navigation menu"'), 'Hamburger must have aria-label');
  assert.ok(navbarCode.includes('aria-expanded={isMobileMenuOpen}'), 'Hamburger must have aria-expanded');
  assert.ok(navbarCode.includes("e.key === 'Escape'"), 'Mobile menu must support Escape key closing');
  assert.ok(navbarCode.includes('onOpenArchitecture'), 'Navbar should support opening architecture modal');
});

test('HeroBanner surfaces 5-second product value and feature proofs', () => {
  const heroPath = path.join(frontendDir, 'src', 'components', 'HeroBanner.jsx');
  assert.ok(fs.existsSync(heroPath), 'HeroBanner component should exist');
  const heroCode = fs.readFileSync(heroPath, 'utf8');

  assert.ok(heroCode.includes('Pinecone Vector RAG'), 'Hero should feature Pinecone Vector RAG');
  assert.ok(heroCode.includes('Pydantic v2 Extraction'), 'Hero should feature Pydantic Extraction');
  assert.ok(heroCode.includes('Tier 0 Security Scaffold'), 'Hero should feature Tier 0 Security');
  assert.ok(heroCode.includes('Dual-Engine LLM Cascade'), 'Hero should feature Dual-Engine Cascade');
});

test('ArchitectureModal defines live topology and failover flow', () => {
  const modalPath = path.join(frontendDir, 'src', 'components', 'ArchitectureModal.jsx');
  assert.ok(fs.existsSync(modalPath), 'ArchitectureModal component should exist');
  const modalCode = fs.readFileSync(modalPath, 'utf8');

  assert.ok(modalCode.includes('FastAPI Backend Engine'), 'Modal should specify FastAPI backend');
  assert.ok(modalCode.includes('Pinecone Vector RAG'), 'Modal should specify Pinecone Vector RAG');
  assert.ok(modalCode.includes('Groq Cloud'), 'Modal should specify Groq Cloud primary');
  assert.ok(modalCode.includes('Google Gemini'), 'Modal should specify Google Gemini fallback');
  assert.ok(modalCode.includes('Aiven PostgreSQL Database'), 'Modal should specify Aiven PostgreSQL');
  assert.ok(modalCode.includes('Gateway:'), 'Modal should verify Gateway subsystem status');
  assert.ok(modalCode.includes('Pinecone:'), 'Modal should verify Pinecone subsystem status');
  assert.ok(modalCode.includes('PostgreSQL:'), 'Modal should verify PostgreSQL subsystem status');
  assert.ok(modalCode.includes('LLM:'), 'Modal should verify LLM subsystem status');
  assert.ok(modalCode.includes('Security:'), 'Modal should verify Security subsystem status');
});

test('ChatTab includes safe prompt injection testing and security event rendering', () => {
  const chatPath = path.join(frontendDir, 'src', 'components', 'ChatTab.jsx');
  const chatCode = fs.readFileSync(chatPath, 'utf8');

  assert.ok(chatCode.includes('Test Attack: Ignore all previous instructions'), 'Chat should offer starter prompt injection test');
  assert.ok(chatCode.includes('security-event-card'), 'Chat should render dedicated security event card');
  assert.ok(chatCode.includes('Why this answer?'), 'Chat should include Why this answer provenance inspection');
});

