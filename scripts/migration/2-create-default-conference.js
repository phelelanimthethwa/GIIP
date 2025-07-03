#!/usr/bin/env node
/**
 * Phase A - Step 2: Create Default Conference Schema
 * This script creates the default conference structure and migrates global settings
 */

const admin = require('firebase-admin');
const path = require('path');

// Initialize Firebase Admin SDK using application default credentials
// Make sure you're logged into Firebase CLI: firebase login
try {
  admin.initializeApp({
    databaseURL: 'https://giir-66ae6-default-rtdb.firebaseio.com'
  });
} catch (error) {
  console.error('❌ Firebase initialization failed. Please run "firebase login" first.');
  process.exit(1);
}

const db = admin.database();

console.log('=== GIIR Conference System - Default Conference Creation ===');
console.log('Phase A - Step 2: Create Default Conference Schema');
console.log('');

async function createDefaultConference() {
  try {
    console.log('📝 Creating default conference structure...');
    
    // Default conference configuration
    const defaultConferenceId = 'default-2025';
    const defaultConference = {
      basic_info: {
        name: "GIIR Conference 2025",
        description: "Global Innovation and Intellectual Research Conference",
        start_date: "2025-07-15T09:00:00Z",
        end_date: "2025-07-17T17:00:00Z",
        status: "active",
        timezone: "UTC",
        year: 2025,
        location: "TBD",
        website: "https://giir-conference.org"
      },
      settings: {
        registration_enabled: true,
        paper_submission_enabled: true,
        review_enabled: true,
        email_notifications: true,
        max_registrations: 1000,
        max_paper_submissions: 500
      },
      metadata: {
        created_at: Date.now(),
        created_by: "migration-script",
        version: "1.0.0",
        migrated_from: "single-conference-system",
        migration_date: new Date().toISOString()
      }
    };

    // Create the default conference
    await db.ref(`conferences/${defaultConferenceId}`).set(defaultConference);
    console.log('✅ Default conference created successfully');

    // Migrate existing global settings to conference-specific settings
    console.log('🔄 Migrating global settings to default conference...');
    
    // Migrate registration fees
    const registrationFeesSnapshot = await db.ref('registration_fees').once('value');
    const registrationFees = registrationFeesSnapshot.val();
    
    if (registrationFees) {
      await db.ref(`conferences/${defaultConferenceId}/registration_fees`).set(registrationFees);
      console.log('✅ Registration fees migrated');
    }

    // Migrate venue details
    const venueDetailsSnapshot = await db.ref('venue_details').once('value');
    const venueDetails = venueDetailsSnapshot.val();
    
    if (venueDetails) {
      await db.ref(`conferences/${defaultConferenceId}/content/venue_details`).set(venueDetails);
      console.log('✅ Venue details migrated');
    }

    // Migrate content sections
    const contentSections = [
      'home_content',
      'about_content', 
      'call_for_papers_content',
      'author_guidelines'
    ];

    for (const section of contentSections) {
      const contentSnapshot = await db.ref(section).once('value');
      const content = contentSnapshot.val();
      
      if (content) {
        await db.ref(`conferences/${defaultConferenceId}/content/${section}`).set(content);
        console.log(`✅ ${section} migrated`);
      }
    }

    // Migrate email templates to conference-specific settings
    const emailTemplatesSnapshot = await db.ref('email_templates').once('value');
    const emailTemplates = emailTemplatesSnapshot.val();
    
    if (emailTemplates) {
      await db.ref(`conferences/${defaultConferenceId}/settings/email_templates`).set(emailTemplates);
      console.log('✅ Email templates migrated');
    }

    // Create global settings collection for system-wide configuration
    console.log('🌐 Creating global settings...');
    const globalSettings = {
      site_design: {
        // Will be populated from existing site_design
        migrated: true
      },
      system_configuration: {
        default_conference: defaultConferenceId,
        multi_conference_enabled: true,
        migration_version: "1.0.0",
        created_at: Date.now()
      }
    };

    // Migrate site design to global settings
    const siteDesignSnapshot = await db.ref('site_design').once('value');
    const siteDesign = siteDesignSnapshot.val();
    
    if (siteDesign) {
      globalSettings.site_design = siteDesign;
    }

    await db.ref('global_settings').set(globalSettings);
    console.log('✅ Global settings created');

    console.log('');
    console.log('=== Schema Creation Complete ===');
    console.log(`✅ Default conference created: ${defaultConferenceId}`);
    console.log('✅ Global settings migrated to conference-specific structure');
    console.log('✅ System-wide global settings created');
    console.log('');
    console.log('🔍 Verification:');
    console.log(`📂 conferences/${defaultConferenceId} - Contains conference-specific data`);
    console.log('📂 global_settings - Contains system-wide configuration');
    console.log('');
    console.log('Next step: Run node 3-deploy-security-rules.js to update security rules');

  } catch (error) {
    console.error('❌ Error creating default conference:', error);
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }
}

async function verifySchemaCreation() {
  try {
    console.log('🔍 Verifying schema creation...');
    
    // Check if default conference exists
    const conferenceSnapshot = await db.ref('conferences/default-2025').once('value');
    if (!conferenceSnapshot.exists()) {
      throw new Error('Default conference was not created');
    }
    
    // Check if global settings exist
    const globalSettingsSnapshot = await db.ref('global_settings').once('value');
    if (!globalSettingsSnapshot.exists()) {
      throw new Error('Global settings were not created');
    }
    
    console.log('✅ Schema creation verified successfully');
    return true;
    
  } catch (error) {
    console.error('❌ Schema verification failed:', error.message);
    return false;
  }
}

// Main execution
async function main() {
  try {
    await createDefaultConference();
    const verified = await verifySchemaCreation();
    
    if (verified) {
      console.log('🎉 Phase A - Step 2 completed successfully!');
      process.exit(0);
    } else {
      console.error('❌ Schema verification failed');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  } finally {
    // Clean up Firebase connection
    await admin.app().delete();
  }
}

// Run the migration
main(); 