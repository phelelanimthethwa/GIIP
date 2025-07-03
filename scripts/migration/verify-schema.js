#!/usr/bin/env node
/**
 * Schema Verification Script
 * Tests the manually created multi-conference schema
 */

const admin = require('firebase-admin');

// Initialize Firebase Admin SDK using application default credentials
try {
  admin.initializeApp({
    databaseURL: 'https://giir-66ae6-default-rtdb.firebaseio.com'
  });
} catch (error) {
  console.error('❌ Firebase initialization failed. Please run "firebase login" first.');
  process.exit(1);
}

const db = admin.database();

console.log('=== GIIR Conference System - Schema Verification ===');
console.log('Verifying manually created multi-conference schema...');
console.log('');

async function verifySchema() {
  const results = {
    passed: 0,
    failed: 0,
    checks: []
  };

  // Test 1: Check if conferences collection exists
  try {
    const conferenceSnapshot = await db.ref('conferences').once('value');
    if (conferenceSnapshot.exists()) {
      results.passed++;
      results.checks.push('✅ conferences collection exists');
    } else {
      results.failed++;
      results.checks.push('❌ conferences collection missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking conferences collection: ' + error.message);
  }

  // Test 2: Check default conference
  try {
    const defaultConfSnapshot = await db.ref('conferences/default-2025').once('value');
    if (defaultConfSnapshot.exists()) {
      results.passed++;
      results.checks.push('✅ default-2025 conference exists');
    } else {
      results.failed++;
      results.checks.push('❌ default-2025 conference missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking default conference: ' + error.message);
  }

  // Test 3: Check basic_info structure
  try {
    const basicInfoSnapshot = await db.ref('conferences/default-2025/basic_info').once('value');
    const basicInfo = basicInfoSnapshot.val();
    
    if (basicInfo && basicInfo.name && basicInfo.status) {
      results.passed++;
      results.checks.push('✅ Conference basic_info structure is valid');
      console.log(`   📋 Conference: ${basicInfo.name}`);
      console.log(`   📅 Status: ${basicInfo.status}`);
    } else {
      results.failed++;
      results.checks.push('❌ Conference basic_info structure invalid or missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking basic_info: ' + error.message);
  }

  // Test 4: Check settings structure
  try {
    const settingsSnapshot = await db.ref('conferences/default-2025/settings').once('value');
    const settings = settingsSnapshot.val();
    
    if (settings && typeof settings.registration_enabled === 'boolean') {
      results.passed++;
      results.checks.push('✅ Conference settings structure is valid');
      console.log(`   🔧 Registration enabled: ${settings.registration_enabled}`);
      console.log(`   📝 Paper submission enabled: ${settings.paper_submission_enabled}`);
    } else {
      results.failed++;
      results.checks.push('❌ Conference settings structure invalid or missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking settings: ' + error.message);
  }

  // Test 5: Check global_settings
  try {
    const globalSettingsSnapshot = await db.ref('global_settings').once('value');
    if (globalSettingsSnapshot.exists()) {
      results.passed++;
      results.checks.push('✅ global_settings collection exists');
    } else {
      results.failed++;
      results.checks.push('❌ global_settings collection missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking global_settings: ' + error.message);
  }

  // Test 6: Check system configuration
  try {
    const sysConfigSnapshot = await db.ref('global_settings/system_configuration').once('value');
    const sysConfig = sysConfigSnapshot.val();
    
    if (sysConfig && sysConfig.default_conference === 'default-2025') {
      results.passed++;
      results.checks.push('✅ System configuration is valid');
      console.log(`   🌐 Default conference: ${sysConfig.default_conference}`);
      console.log(`   🔄 Multi-conference enabled: ${sysConfig.multi_conference_enabled}`);
    } else {
      results.failed++;
      results.checks.push('❌ System configuration invalid or missing');
    }
  } catch (error) {
    results.failed++;
    results.checks.push('❌ Error checking system configuration: ' + error.message);
  }

  return results;
}

async function main() {
  try {
    const results = await verifySchema();
    
    console.log('');
    console.log('=== Verification Results ===');
    
    results.checks.forEach(check => console.log(check));
    
    console.log('');
    console.log(`📊 Summary: ${results.passed} passed, ${results.failed} failed`);
    
    if (results.failed === 0) {
      console.log('');
      console.log('🎉 Schema verification PASSED!');
      console.log('✅ Multi-conference schema is properly configured');
      console.log('🚀 Ready to proceed to Phase B - Data Migration');
      console.log('');
      console.log('Next steps:');
      console.log('  1. Test basic application functionality');
      console.log('  2. Begin Phase B migration scripts');
      console.log('  3. Migrate existing data to new structure');
    } else {
      console.log('');
      console.log('❌ Schema verification FAILED!');
      console.log('🔧 Please check the Firebase Console and correct the issues above');
      console.log('📖 Refer to the manual creation guide in the status report');
    }
    
  } catch (error) {
    console.error('❌ Verification failed:', error);
    process.exit(1);
  } finally {
    // Clean up Firebase connection
    await admin.app().delete();
  }
}

// Run the verification
main(); 