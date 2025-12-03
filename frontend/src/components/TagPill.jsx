import PropTypes from 'prop-types';
import { getPastelColorFromString, getContrastingTextColor } from '../utils/colors';

export default function TagPill({ tag, selected, onRemove, onClick, clickable }) {
    // Generate pastel color from tag name
    const backgroundColor = getPastelColorFromString(tag.name);
    const textColor = getContrastingTextColor(backgroundColor);
    
    const classes = [
        'tag-pill',
        clickable && 'tag-pill--clickable',
        selected && 'tag-pill--selected',
        onRemove && 'tag-pill--removable',
    ].filter(Boolean).join(' ');
    
    const style = {
        backgroundColor,
        color: textColor,
        borderColor: selected ? 'rgba(15, 23, 42, 0.25)' : 'rgba(15, 23, 42, 0.08)',
    };

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
        <span className={classes} style={style} onClick={handleClick}>
            {tag.name}
            {onRemove && (
                <button
                    className="tag-pill__remove"
                    onClick={handleRemove}
                    type="button"
                    aria-label={`Remove ${tag.name} tag`}
                    style={{ color: textColor }}
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
