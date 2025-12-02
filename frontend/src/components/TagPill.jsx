import PropTypes from 'prop-types';

export default function TagPill({ tag, selected, onRemove, onClick, clickable }) {
    const colorClass = `tag-pill--${tag.color_scheme || 'generic'}`;
    const classes = [
        'tag-pill',
        colorClass,
        clickable && 'tag-pill--clickable',
        selected && 'tag-pill--selected',
        onRemove && 'tag-pill--removable',
    ].filter(Boolean).join(' ');

    const handleClick = () => {
        if (clickable && onClick) {
            onClick(tag);
        }
    };

    const handleRemove = (e) => {
        e.stopPropagation();
        if (onRemove) {
            onRemove(tag);
        }
    };

    return (
        <span className={classes} onClick={handleClick}>
            {tag.name}
            {onRemove && (
                <button
                    className="tag-pill__remove"
                    onClick={handleRemove}
                    type="button"
                    aria-label={`Remove ${tag.name} tag`}
                >
                    ×
                </button>
            )}
        </span>
    );
}

TagPill.propTypes = {
    tag: PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        color_scheme: PropTypes.string,
    }).isRequired,
    selected: PropTypes.bool,
    onRemove: PropTypes.func,
    onClick: PropTypes.func,
    clickable: PropTypes.bool,
};

TagPill.defaultProps = {
    selected: false,
    onRemove: null,
    onClick: null,
    clickable: false,
};
