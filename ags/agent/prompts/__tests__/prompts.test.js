const { loadPrompts, renderPrompt, getPrompt } = require('../prompts');
const path = require('path');

describe('Prompt Utilities', () => {
    const testPromptsFile = path.join(__dirname, '../../../../assets/prompts/prompts.yaml');
    
    describe('renderPrompt', () => {
        it('should replace variables in template', () => {
            const template = 'Hello {{name}}! Welcome to {{place}}';
            const variables = {
                name: 'John',
                place: 'World'
            };
            expect(renderPrompt(template, variables)).toBe('Hello John! Welcome to World');
        });

        it('should leave unmatched variables unchanged', () => {
            const template = 'Hello {{name}}! Welcome to {{place}}';
            const variables = {
                name: 'John'
            };
            expect(renderPrompt(template, variables)).toBe('Hello John! Welcome to {{place}}');
        });
    });

    describe('getPrompt', () => {
        it('should load and render a prompt from YAML', () => {
            const variables = {
                database_name: 'test_db'
            };
            const prompt = getPrompt('system.storage', variables);
            expect(prompt).toContain('test_db');
        });

        it('should throw error for non-existent prompt', () => {
            expect(() => getPrompt('nonexistent.prompt')).toThrow();
        });
    });
}); 