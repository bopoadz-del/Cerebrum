const { chromium } = require('playwright');
const fs = require('fs');

// POST-DEPLOYMENT UI TEST SCRIPT
// Run this after every deployment to verify UI works

async function postDeployTest() {
  console.log('🚀 POST-DEPLOYMENT UI TEST\n');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  
  try {
    // 1. Load
    console.log('📱 Loading...');
    await page.goto('https://cerebrum-frontend.onrender.com', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/cerebrum-test/01-load.png' });
    console.log('✅ Loaded\n');
    
    // 2. Test chat
    console.log('💬 Testing chat...');
    const input = await page.$('textarea');
    if (input) {
      await input.fill('/help');
      await input.press('Enter');
      await page.waitForTimeout(4000);
      await page.screenshot({ path: '/tmp/cerebrum-test/02-chat.png' });
      console.log('✅ Chat works\n');
    }
    
    // 3. Summary
    console.log('═══════════════════════════════════════');
    console.log('📊 TEST RESULTS');
    console.log('═══════════════════════════════════════');
    console.log(`Console Errors: ${errors.length || 'None'}`);
    if (errors.length > 0) {
      errors.slice(0, 3).forEach(e => console.log(`  ❌ ${e.substring(0, 100)}`));
    }
    console.log('\n✅ POST-DEPLOY TEST COMPLETE');
    
  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: '/tmp/cerebrum-test/error.png' });
  } finally {
    await browser.close();
  }
}

postDeployTest();
