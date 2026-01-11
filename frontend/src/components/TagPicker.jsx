import { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import TagPill from './TagPill';
import { validateContent, sanitizeText } from '../utils/security';

export default function TagPicker({ onTagSelect, existingTagIds = [] }) {
    const [isOpen, setIsOpen] = useState(false);
    const [tags, setTags] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const { token } = useAuth();
    const dropdownRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            fetchTags();
        }
    }, [isOpen]);

    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchTags = async () => {
        setLoading(true);
        try {
            const data = await api.getTags(token);
            setTags(data);
        } catch (err) {
            console.error('Failed to fetch tags', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateTag = async () => {
        if (!searchQuery.trim()) return;

        // Validate tag name (tags should be shorter, max 50 chars)
        const validation = validateContent(searchQuery, 50);
        if (!validation.isValid) {
            alert(validation.error || 'Invalid tag name');
            return;
        }

        try {
            const newTag = await api.createTag(token, validation.sanitized);
            setTags([...tags, newTag]);
            onTagSelect(newTag);
            setSearchQuery('');
            setIsOpen(false);
        } catch (err) {
            alert(err.message);
        }
    };

    const handleSelectTag = (tag) => {
        onTagSelect(tag);
        setIsOpen(false);
        setSearchQuery('');
    };

    const filteredTags = tags.filter(
        (tag) =>
            !existingTagIds.includes(tag.id) &&
            tag.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const showCreateOption = searchQuery.trim() && !filteredTags.some(
        (tag) => tag.name.toLowerCase() === searchQuery.toLowerCase()
    );

    return (
        <div className="tag-picker" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="secondary"
            >
                + Add Tag
            </button>

            {isOpen && (
                <div className="tag-picker__dropdown">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search or create tag..."
                        className="tag-picker__search"
                        autoFocus
                    />

                    <div className="tag-picker__list">
                        {loading ? (
                            <div className="tag-picker__item">Loading...</div>
                        ) : (
                            <>
                                {filteredTags.map((tag) => (
                                    <div
                                        key={tag.id}
                                        className="tag-picker__item"
                                        onClick={() => handleSelectTag(tag)}
                                    >
                                        <TagPill tag={tag} />
                                    </div>
                                ))}

                                {showCreateOption && (
                                    <div
                                        className="tag-picker__item"
                                        onClick={handleCreateTag}
                                        style={{ fontStyle: 'italic', color: 'var(--color-olive)' }}
                                    >
                                        Create "{sanitizeText(searchQuery)}"
                                    </div>
                                )}

                                {filteredTags.length === 0 && !showCreateOption && (
                                    <div className="tag-picker__item" style={{ opacity: 0.6 }}>
                                        No tags found
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

TagPicker.propTypes = {
    onTagSelect: PropTypes.func.isRequired,
    existingTagIds: PropTypes.arrayOf(PropTypes.number),
};
