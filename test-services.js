const { chromium } = require('playwright');

async function testServices() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    console.log('Testing Mission Control (port 5000)...');
    await page.goto('http://localhost:5000');
    const missionTitle = await page.title();
    console.log('✓ Mission Control title:', missionTitle);
    
    // Check for key elements
    const sections = await page.$$('.section');
    console.log('✓ Found', sections.length, 'sections on Mission Control');
    
    console.log('\nTesting Telemetry Dashboard (port 5001)...');
    await page.goto('http://localhost:5001');
    const telemetryTitle = await page.title();
    console.log('✓ Telemetry Dashboard title:', telemetryTitle);
    
    // Check telemetry fields
    const altitude = await page.$('#altitude');
    const speed = await page.$('#speed');
    const fuel = await page.$('#fuel');
    console.log('✓ Telemetry fields present:', !!altitude, !!speed, !!fuel);
    
    console.log('\nBoth services are responding correctly!');
    
  } catch (error) {
    console.error('Error testing services:', error.message);
  } finally {
    await browser.close();
  }
}

testServices();