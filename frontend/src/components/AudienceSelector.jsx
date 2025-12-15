import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import TagPill from './TagPill';

export default function AudienceSelector({ onAudienceChange }) {
    const [isOpen, setIsOpen] = useState(false);
    const [audienceType, setAudienceType] = useState('all');
    const [selectedTags, setSelectedTags] = useState([]);
    const [tags, setTags] = useState([]);
    const { token } = useAuth();

    useEffect(() => {
        fetchTags();
    }, []);

    useEffect(() => {
        onAudienceChange({
            audience_type: audienceType,
            audience_tag_ids: selectedTags.map(t => t.id),
        });
    }, [audienceType, selectedTags]);

    const fetchTags = async () => {
        try {
            const data = await api.getTags(token);
            setTags(data);
        } catch (err) {
            console.error('Failed to fetch tags', err);
        }
    };

    const handleTypeChange = (type) => {
        setAudienceType(type);
        if (type !== 'tags') {
            setSelectedTags([]);
        }
    };

    const handleTagToggle = (tag) => {
        if (selectedTags.find(t => t.id === tag.id)) {
            setSelectedTags(selectedTags.filter(t => t.id !== tag.id));
        } else {
            setSelectedTags([...selectedTags, tag]);
        }
    };

    const getAudienceSummary = () => {
        if (audienceType === 'all') return 'All connections';
        if (audienceType === 'private') return 'Only me';
        if (audienceType === 'tags') {
            if (selectedTags.length === 0) return 'Select tags...';
            return selectedTags.map(t => t.name).join(', ');
        }
        return 'All connections';
    };

    return (
        <div className="audience-selector">
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="audience-pill"
                aria-label="Select audience"
                aria-expanded={isOpen}
            >
                <span className="audience-pill-icon">👁️</span>
                <span className="audience-pill-text">{getAudienceSummary()}</span>
            </button>

            {isOpen && (
                <div className="audience-modal" onClick={(e) => e.target === e.currentTarget && setIsOpen(false)}>
                    <div className="audience-modal__content" role="dialog" aria-labelledby="audience-modal-title">
                        <h3 id="audience-modal-title">Choose who can see this post</h3>
                        <p className="subtitle">Control the visibility of your post</p>

                        <div className="audience-options">
                            <label className="audience-option">
                                <input
                                    type="radio"
                                    name="audience"
                                    checked={audienceType === 'all'}
                                    onChange={() => handleTypeChange('all')}
                                />
                                <div>
                                    <strong>All connections</strong>
                                    <span>Everyone you're connected with</span>
                                </div>
                            </label>

                            <label className="audience-option">
                                <input
                                    type="radio"
                                    name="audience"
                                    checked={audienceType === 'private'}
                                    onChange={() => handleTypeChange('private')}
                                />
                                <div>
                                    <strong>Only me</strong>
                                    <span>Private journal entry</span>
                                </div>
                            </label>

                            <label className="audience-option">
                                <input
                                    type="radio"
                                    name="audience"
                                    checked={audienceType === 'tags'}
                                    onChange={() => handleTypeChange('tags')}
                                />
                                <div>
                                    <strong>Selected tags</strong>
                                    <span>Choose specific groups</span>
                                </div>
                            </label>
                        </div>

                        {audienceType === 'tags' && (
                            <div className="tag-selection">
                                <p className="tag-selection__label">Select tags:</p>
                                <div className="tag-grid">
                                    {tags.length === 0 ? (
                                        <p className="tag-selection__empty">
                                            No tags yet. Add tags to your connections first.
                                        </p>
                                    ) : (
                                        tags.map((tag) => (
                                            <TagPill
                                                key={tag.id}
                                                tag={tag}
                                                clickable
                                                selected={selectedTags.some(t => t.id === tag.id)}
                                                onClick={handleTagToggle}
                                            />
                                        ))
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="audience-actions">
                            <button type="button" onClick={() => setIsOpen(false)} className="btn-primary">
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

AudienceSelector.propTypes = {
    onAudienceChange: PropTypes.func.isRequired,
};
