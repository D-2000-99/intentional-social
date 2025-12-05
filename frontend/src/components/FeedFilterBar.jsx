import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import TagPill from './TagPill';

export default function FeedFilterBar({ onFilterChange }) {
    const [tags, setTags] = useState([]);
    const [selectedTagIds, setSelectedTagIds] = useState([]);
    const { token } = useAuth();

    useEffect(() => {
        fetchTags();
    }, []);

    useEffect(() => {
        onFilterChange(selectedTagIds);
    }, [selectedTagIds]);

    const fetchTags = async () => {
        try {
            const data = await api.getTags(token);
            setTags(data);
        } catch (err) {
            console.error('Failed to fetch tags', err);
        }
    };

    const handleTagClick = (tag) => {
        if (selectedTagIds.includes(tag.id)) {
            setSelectedTagIds(selectedTagIds.filter((id) => id !== tag.id));
        } else {
            setSelectedTagIds([...selectedTagIds, tag.id]);
        }
    };

    const handleClearFilters = () => {
        setSelectedTagIds([]);
    };

    if (tags.length === 0) {
        return null;
    }

    return (
        <div>
            <div className="feed-filters">
                <button
                    className={`filter-pill ${selectedTagIds.length === 0 ? 'active' : ''}`}
                    onClick={handleClearFilters}
                >
                    All Posts
                </button>
                {tags.map((tag) => (
                    <button
                        key={tag.id}
                        className={`filter-pill ${selectedTagIds.includes(tag.id) ? 'active' : ''}`}
                        onClick={() => handleTagClick(tag)}
                    >
                        {tag.name}
                    </button>
                ))}
            </div>

            {selectedTagIds.length > 0 && (
                <div className="tag-filter-summary">
                    Showing posts from: {tags.filter(t => selectedTagIds.includes(t.id)).map(t => t.name).join(', ')}
                    <button onClick={handleClearFilters}>Clear filters</button>
                </div>
            )}
        </div>
    );
}

FeedFilterBar.propTypes = {
    onFilterChange: PropTypes.func.isRequired,
};
