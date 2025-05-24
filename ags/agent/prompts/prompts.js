const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');

/**
 * Loads prompts from a YAML file
 * @param {string} promptsFile - Path to the YAML file containing prompts
 * @returns {Object} The loaded prompts object
 */
function loadPrompts(promptsFile = path.join(__dirname, '../../../assets/prompts/prompts.yaml')) {
    try {
        const fileContents = fs.readFileSync(promptsFile, 'utf8');
        return yaml.load(fileContents);
    } catch (error) {
        console.error('Error loading prompts:', error);
        throw error;
    }
}

/**
 * Renders a prompt template by replacing variables in {{ }} with their values
 * @param {string} template - The template string containing variables in {{ }}
 * @param {Object} variables - Optional object mapping variable names to their values
 * @returns {string} The rendered prompt with variables replaced
 */
function renderPrompt(template, variables = {}) {
    return template.replace(/\{\{([^}]+)\}\}/g, (match, varName) => {
        const trimmedVarName = varName.trim();
        return variables[trimmedVarName] !== undefined ? variables[trimmedVarName] : match;
    });
}

/**
 * Gets a specific prompt by name and renders it with the given variables
 * @param {string} promptName - Name of the prompt to retrieve (e.g., 'system.storage')
 * @param {Object} variables - Optional object mapping variable names to their values
 * @returns {string} The rendered prompt string
 */
function getPrompt(promptName, variables = {}) {
    const prompts = loadPrompts();
    
    // Handle nested keys (e.g., 'system.storage')
    const keys = promptName.split('.');
    let current = prompts;
    
    for (const key of keys) {
        if (current[key] === undefined) {
            throw new Error(`Prompt '${promptName}' not found`);
        }
        current = current[key];
    }
    
    return renderPrompt(current, variables);
}

module.exports = {
    loadPrompts,
    renderPrompt,
    getPrompt
};
