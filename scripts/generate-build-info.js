const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Get the last commit date from local git
function getLastCommitDate() {
  try {
    const date = execSync('git log -1 --format=%ci', { encoding: 'utf-8' }).trim();
    return date;
  } catch (error) {
    console.error('Error getting last commit date:', error);
    return null;
  }
}

// Create a JSON file with the build info
function generateBuildInfo() {
  const lastCommitDate = getLastCommitDate();
  
  const buildInfo = {
    lastUpdated: lastCommitDate,
    buildTime: new Date().toISOString()
  };

  const publicDir = path.join(__dirname, 'public');
  
  // Create public directory if it doesn't exist
  if (!fs.existsSync(publicDir)) {
    fs.mkdirSync(publicDir, { recursive: true });
  }
  
  fs.writeFileSync(
    path.join(publicDir, 'build-info.json'),
    JSON.stringify(buildInfo, null, 2)
  );
  
  console.log('Build info generated:', buildInfo);
}

generateBuildInfo();
