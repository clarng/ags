/**
 * Persona Fusion Chart - Reverse Lookup
 * Shows all combinations needed to create each persona type
 */

// Arcana types in order
const ARCANA = [
  'Fool', 'Magician', 'Priestess', 'Empress', 'Emperor', 'Hierophant',
  'Lovers', 'Chariot', 'Justice', 'Hermit', 'Fortune', 'Strength',
  'Hanged', 'Death', 'Temperance', 'Devil', 'Tower', 'Star',
  'Moon', 'Sun', 'Judgement', 'Faith', 'Councillor', 'World'
];

// Fusion table: fusionTable[row][col] = result arcana
// "-" means no fusion possible
const fusionTable = {
  'Fool': { 'Fool': 'Fool', 'Magician': 'Death', 'Priestess': 'Moon', 'Empress': 'Hanged', 'Emperor': 'Temperance', 'Hierophant': 'Hermit', 'Lovers': 'Chariot', 'Chariot': 'Moon', 'Justice': 'Star', 'Hermit': 'Priestess', 'Fortune': 'Faith', 'Strength': 'Death', 'Hanged': 'Tower', 'Death': 'Strength', 'Temperance': 'Hierophant', 'Devil': 'Temperance', 'Tower': 'Empress', 'Star': 'Magician', 'Moon': 'Justice', 'Sun': 'Justice', 'Judgement': 'Sun', 'Faith': 'Councillor', 'Councillor': 'Hierophant', 'World': 'None' },
  'Magician': { 'Fool': '-', 'Magician': 'Magician', 'Priestess': 'Temperance', 'Empress': 'Justice', 'Emperor': 'Faith', 'Hierophant': 'Death', 'Lovers': 'Devil', 'Chariot': 'Priestess', 'Justice': 'Emperor', 'Hermit': 'Lovers', 'Fortune': 'Justice', 'Strength': 'Fool', 'Hanged': 'Empress', 'Death': 'Hermit', 'Temperance': 'Chariot', 'Devil': 'Hierophant', 'Tower': 'Temperance', 'Star': 'Priestess', 'Moon': 'Lovers', 'Sun': 'Hierophant', 'Judgement': 'Strength', 'Faith': 'Strength', 'Councillor': 'Moon', 'World': 'None' },
  'Priestess': { 'Fool': '-', 'Magician': '-', 'Priestess': 'Priestess', 'Empress': 'Emperor', 'Emperor': 'Empress', 'Hierophant': 'Magician', 'Lovers': 'Fortune', 'Chariot': 'Hierophant', 'Justice': 'Death', 'Hermit': 'Temperance', 'Fortune': 'Magician', 'Strength': 'Devil', 'Hanged': 'Death', 'Death': 'Magician', 'Temperance': 'Devil', 'Devil': 'Moon', 'Tower': 'Hanged', 'Star': 'Hermit', 'Moon': 'Hierophant', 'Sun': 'Chariot', 'Judgement': 'Justice', 'Faith': 'Justice', 'Councillor': 'Faith', 'World': 'None' },
  'Empress': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': 'Empress', 'Emperor': 'Justice', 'Hierophant': 'Fool', 'Lovers': 'Judgement', 'Chariot': 'Star', 'Justice': 'Lovers', 'Hermit': 'Strength', 'Fortune': 'Hermit', 'Strength': 'Faith', 'Hanged': 'Priestess', 'Death': 'Fool', 'Temperance': 'Faith', 'Devil': 'Sun', 'Tower': 'Emperor', 'Star': 'Lovers', 'Moon': 'Fortune', 'Sun': 'Tower', 'Judgement': 'Emperor', 'Faith': 'Magician', 'Councillor': 'Hanged', 'World': 'None' },
  'Emperor': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': 'Emperor', 'Hierophant': 'Fortune', 'Lovers': 'Fool', 'Chariot': 'Faith', 'Justice': 'Chariot', 'Hermit': 'Hierophant', 'Fortune': 'Sun', 'Strength': 'Tower', 'Hanged': 'Devil', 'Death': 'Hermit', 'Temperance': 'Devil', 'Devil': 'Justice', 'Tower': 'Star', 'Star': 'Lovers', 'Moon': 'Tower', 'Sun': 'Judgement', 'Judgement': 'Priestess', 'Faith': 'Priestess', 'Councillor': 'Lovers', 'World': 'None' },
  'Hierophant': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': 'Hierophant', 'Lovers': 'Strength', 'Chariot': 'Star', 'Justice': 'Hanged', 'Hermit': 'Councillor', 'Fortune': 'Justice', 'Strength': 'Fool', 'Hanged': 'Sun', 'Death': 'Chariot', 'Temperance': 'Death', 'Devil': 'Hanged', 'Tower': 'Judgement', 'Star': 'Tower', 'Moon': 'Priestess', 'Sun': 'Lovers', 'Judgement': 'Faith', 'Faith': 'Empress', 'Councillor': 'Justice', 'World': 'None' },
  'Lovers': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': 'Lovers', 'Chariot': 'Temperance', 'Justice': 'Judgement', 'Hermit': 'Chariot', 'Fortune': 'Strength', 'Strength': 'Death', 'Hanged': 'Councillor', 'Death': 'Temperance', 'Temperance': 'Strength', 'Devil': 'Moon', 'Tower': 'Empress', 'Star': 'Faith', 'Moon': 'Magician', 'Sun': 'Empress', 'Judgement': 'Hanged', 'Faith': 'Tower', 'Councillor': 'Tower', 'World': 'None' },
  'Chariot': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': 'Chariot', 'Justice': 'Moon', 'Hermit': 'Devil', 'Fortune': 'Councillor', 'Strength': 'Hermit', 'Hanged': 'Fool', 'Death': 'Devil', 'Temperance': 'Strength', 'Devil': 'Temperance', 'Tower': 'Fortune', 'Star': 'Moon', 'Moon': 'Lovers', 'Sun': 'Priestess', 'Judgement': 'None', 'Faith': 'Lovers', 'Councillor': 'Sun', 'World': 'None' },
  'Justice': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': 'Justice', 'Hermit': 'Magician', 'Fortune': 'Emperor', 'Strength': 'Councillor', 'Hanged': 'Lovers', 'Death': 'Fool', 'Temperance': 'Emperor', 'Devil': 'Fool', 'Tower': 'Sun', 'Star': 'Empress', 'Moon': 'Devil', 'Sun': 'Hanged', 'Judgement': 'None', 'Faith': 'Hanged', 'Councillor': 'Emperor', 'World': 'None' },
  'Hermit': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': 'Hermit', 'Fortune': 'Star', 'Strength': 'Hierophant', 'Hanged': 'Star', 'Death': 'Strength', 'Temperance': 'Strength', 'Devil': 'Priestess', 'Tower': 'Judgement', 'Star': 'Strength', 'Moon': 'Priestess', 'Sun': 'Devil', 'Judgement': 'Emperor', 'Faith': 'Judgement', 'Councillor': 'Faith', 'World': 'None' },
  'Fortune': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': 'Fortune', 'Strength': 'Faith', 'Hanged': 'Emperor', 'Death': 'Star', 'Temperance': 'Empress', 'Devil': 'Hierophant', 'Tower': 'Hanged', 'Star': 'Devil', 'Moon': 'Sun', 'Sun': 'Star', 'Judgement': 'Tower', 'Faith': 'Councillor', 'Councillor': 'Judgement', 'World': 'None' },
  'Strength': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': 'Strength', 'Hanged': 'Temperance', 'Death': 'Hierophant', 'Temperance': 'Chariot', 'Devil': 'Death', 'Tower': 'Faith', 'Star': 'Moon', 'Moon': 'Magician', 'Sun': 'Moon', 'Judgement': 'None', 'Faith': 'Star', 'Councillor': 'Empress', 'World': 'None' },
  'Hanged': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': 'Hanged', 'Death': 'Moon', 'Temperance': 'Death', 'Devil': 'Fortune', 'Tower': 'Hermit', 'Star': 'Justice', 'Moon': 'Councillor', 'Sun': 'Hierophant', 'Judgement': 'Star', 'Faith': 'Devil', 'Councillor': 'Star', 'World': 'None' },
  'Death': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': 'Death', 'Temperance': 'Hanged', 'Devil': 'Chariot', 'Tower': 'Sun', 'Star': 'Councillor', 'Moon': 'Hierophant', 'Sun': 'Priestess', 'Judgement': 'None', 'Faith': 'Fool', 'Councillor': 'Magician', 'World': 'None' },
  'Temperance': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': 'Temperance', 'Devil': 'Fool', 'Tower': 'Fortune', 'Star': 'Sun', 'Moon': 'Councillor', 'Sun': 'Magician', 'Judgement': 'Hermit', 'Faith': 'Hermit', 'Councillor': 'Fool', 'World': 'None' },
  'Devil': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': 'Devil', 'Tower': 'Magician', 'Star': 'Strength', 'Moon': 'Chariot', 'Sun': 'Hermit', 'Judgement': 'Lovers', 'Faith': 'Chariot', 'Councillor': 'Chariot', 'World': 'None' },
  'Tower': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': 'Tower', 'Star': 'Councillor', 'Moon': 'Hermit', 'Sun': 'Emperor', 'Judgement': 'Moon', 'Faith': 'Death', 'Councillor': 'Death', 'World': 'None' },
  'Star': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': 'Star', 'Moon': 'Temperance', 'Sun': 'Judgement', 'Judgement': 'Fortune', 'Faith': 'Temperance', 'Councillor': 'Sun', 'World': 'None' },
  'Moon': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': 'Moon', 'Sun': 'Empress', 'Judgement': 'Fool', 'Faith': 'Sun', 'Councillor': 'Temperance', 'World': 'None' },
  'Sun': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': '-', 'Sun': 'Sun', 'Judgement': 'Death', 'Faith': 'Emperor', 'Councillor': 'Fortune', 'World': 'None' },
  'Judgement': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': '-', 'Sun': '-', 'Judgement': 'Judgement', 'Faith': 'Fortune', 'Councillor': 'Devil', 'World': 'None' },
  'Faith': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': '-', 'Sun': '-', 'Judgement': '-', 'Faith': 'Faith', 'Councillor': 'Priestess', 'World': 'None' },
  'Councillor': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': '-', 'Sun': '-', 'Judgement': '-', 'Faith': '-', 'Councillor': 'Councillor', 'World': 'None' },
  'World': { 'Fool': '-', 'Magician': '-', 'Priestess': '-', 'Empress': '-', 'Emperor': '-', 'Hierophant': '-', 'Lovers': '-', 'Chariot': '-', 'Justice': '-', 'Hermit': '-', 'Fortune': '-', 'Strength': '-', 'Hanged': '-', 'Death': '-', 'Temperance': '-', 'Devil': '-', 'Tower': '-', 'Star': '-', 'Moon': '-', 'Sun': '-', 'Judgement': '-', 'Faith': '-', 'Councillor': '-', 'World': 'World' }
};

/**
 * Get all combinations that create a specific persona type
 */
function getCombinationsFor(targetArcana) {
  const combinations = [];

  for (const row of ARCANA) {
    for (const col of ARCANA) {
      // Skip if row comes after col (to avoid duplicates since A+B = B+A)
      if (ARCANA.indexOf(row) > ARCANA.indexOf(col)) continue;

      const result = fusionTable[row]?.[col];
      if (result === targetArcana) {
        combinations.push(`${row} + ${col}`);
      }
    }
  }

  return combinations;
}

/**
 * Generate a reverse lookup table showing all combinations for each arcana
 */
function generateReverseLookup() {
  const reverseLookup = {};

  for (const arcana of ARCANA) {
    reverseLookup[arcana] = getCombinationsFor(arcana);
  }

  return reverseLookup;
}

/**
 * Print all combinations for a specific arcana
 */
function printCombinationsFor(targetArcana) {
  const combos = getCombinationsFor(targetArcana);
  console.log(`\n=== Combinations to create ${targetArcana} (${combos.length} total) ===`);
  combos.forEach(combo => console.log(`  ${combo}`));
}

/**
 * Generate CSV output for spreadsheet
 */
function generateCSV() {
  const reverseLookup = generateReverseLookup();

  // Find max number of combinations for any arcana
  let maxCombos = 0;
  for (const arcana of ARCANA) {
    maxCombos = Math.max(maxCombos, reverseLookup[arcana].length);
  }

  // Header row
  let csv = 'Target Arcana';
  for (let i = 1; i <= maxCombos; i++) {
    csv += `,Combo ${i}`;
  }
  csv += '\n';

  // Data rows
  for (const arcana of ARCANA) {
    const combos = reverseLookup[arcana];
    csv += arcana;
    for (let i = 0; i < maxCombos; i++) {
      csv += ',' + (combos[i] || '');
    }
    csv += '\n';
  }

  return csv;
}

/**
 * Print full reverse lookup table
 */
function printFullTable() {
  console.log('\n========================================');
  console.log('PERSONA FUSION - REVERSE LOOKUP TABLE');
  console.log('========================================\n');

  for (const arcana of ARCANA) {
    printCombinationsFor(arcana);
  }
}

// Main execution
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log('Usage:');
  console.log('  node persona-fusion.js all          - Show all combinations for all arcana');
  console.log('  node persona-fusion.js csv          - Output CSV format for spreadsheet');
  console.log('  node persona-fusion.js <arcana>     - Show combinations for specific arcana');
  console.log('\nExample: node persona-fusion.js Magician');
  console.log('\nAvailable Arcana:');
  console.log(ARCANA.join(', '));
} else if (args[0].toLowerCase() === 'all') {
  printFullTable();
} else if (args[0].toLowerCase() === 'csv') {
  console.log(generateCSV());
} else {
  const target = args[0];
  // Case-insensitive match
  const matched = ARCANA.find(a => a.toLowerCase() === target.toLowerCase());
  if (matched) {
    printCombinationsFor(matched);
  } else {
    console.log(`Unknown arcana: ${target}`);
    console.log('Available Arcana:', ARCANA.join(', '));
  }
}

module.exports = { getCombinationsFor, generateReverseLookup, generateCSV, ARCANA };
