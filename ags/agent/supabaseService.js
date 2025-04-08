const { createClient } = require('@supabase/supabase-js');

class SupabaseService {
    constructor(supabaseUrl, supabaseKey) {
        if (!supabaseUrl || !supabaseKey) {
            throw new Error('Supabase URL and Key are required');
        }
        this.supabase = createClient(supabaseUrl, supabaseKey);
    }

    /**
     * Save a conversation to Supabase
     * @param {string} userId - User identifier
     * @param {Array} messages - Array of conversation messages
     * @param {string} [conversationId] - Optional conversation ID for updates
     * @returns {Promise<Object>} - Saved conversation data
     */
    async saveConversation(userId, messages, conversationId = null) {
        try {
            const conversationData = {
                user_id: userId,
                id: conversationId,
                messages: messages,
                updated_at: new Date().toISOString()
            };

            // Create new conversation
            const { data, error } = await this.supabase
                .from('conversations')
                .upsert(conversationData)
                .select()
                .single();

            if (error) throw error;
            return data;

        } catch (error) {
            console.error('Error saving conversation:', error);
            throw error;
        }
    }

    /**
     * Get all conversations for a user
     * @param {string} userId - User identifier
     * @returns {Promise<Array>} - Array of conversations
     */
    async getConversations(userId) {
        try {
            console.log('Fetching conversations for userId:', userId);
            
            if (!userId) {
                throw new Error('userId is required');
            }

            const { data, error } = await this.supabase
                .from('conversations')
                .select('*')
                .eq('user_id', userId)
                .order('updated_at', { ascending: false });

            if (error) {
                console.error('Supabase error:', error);
                throw error;
            }

            console.log('Retrieved conversations:', data);
            return data;
        } catch (error) {
            console.error('Error in getConversations:', error);
            throw error;
        }
    }

    /**
     * Get a specific conversation by ID
     * @param {string} userId - User identifier
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} - Conversation data
     */
    async getConversation(userId, conversationId) {
        try {
            const { data, error } = await this.supabase
                .from('conversations')
                .select('*')
                .eq('user_id', userId)
                .eq('id', conversationId)
                .single();

            if (error) throw error;
            return data;
        } catch (error) {
            console.error('Error getting conversation:', error);
            throw error;
        }
    }

    /**
     * Delete a conversation
     * @param {string} userId - User identifier
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} - Deletion result
     */
    async deleteConversation(userId, conversationId) {
        try {
            const { data, error } = await this.supabase
                .from('conversations')
                .delete()
                .eq('user_id', userId)
                .eq('id', conversationId)
                .select()
                .single();

            if (error) throw error;
            return data;
        } catch (error) {
            console.error('Error deleting conversation:', error);
            throw error;
        }
    }

    /**
     * Save a photo to Supabase storage
     * @param {string} userId - User identifier
     * @param {string} base64Photo - Base64 encoded photo
     * @param {string} [filename] - Optional filename
     * @returns {Promise<string>} - Public URL of the saved photo
     */
    async savePhoto(userId, base64Photo, filename = null) {
        try {
            // Convert base64 to buffer
            const buffer = Buffer.from(base64Photo, 'base64');
            
            // Generate filename if not provided
            const photoFilename = filename || `${userId}_${Date.now()}.jpg`;
            
            // Upload to Supabase storage
            const { data, error } = await this.supabase.storage
                .from('photos')
                .upload(photoFilename, buffer, {
                    contentType: 'image/jpeg',
                    upsert: true
                });

            if (error) throw error;

            // Get public URL
            const { data: { publicUrl } } = this.supabase.storage
                .from('photos')
                .getPublicUrl(photoFilename);

            return publicUrl;
        } catch (error) {
            console.error('Error saving photo:', error);
            throw error;
        }
    }
}

module.exports = SupabaseService; 