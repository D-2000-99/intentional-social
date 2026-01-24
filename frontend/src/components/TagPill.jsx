import PropTypes from 'prop-types';
import { getPastelColorFromString, getContrastingTextColor } from '../utils/colors';
import { sanitizeText, sanitizeUrlParam } from '../utils/security';
import { X } from 'lucide-react';

export default function TagPill({ tag, selected, onRemove, onClick, clickable }) {
    // Use predefined color scheme if available, otherwise generate from name
    const colorScheme = tag.color_scheme || 'generic';
    const usePredefined = ['family', 'friends', 'inner', 'work'].includes(colorScheme);
    
    let backgroundColor, textColor;
    
    if (usePredefined) {
        // Use CSS variables for predefined schemes
        const classes = [
            'tag-pill',
            `tag-pill--${colorScheme}`,
            clickable && 'tag-pill--clickable',
            selected && 'tag-pill--selected',
            onRemove && 'tag-pill--removable',
        ].filter(Boolean).join(' ');
        
        const style = {
            borderColor: selected ? 'rgba(15, 23, 42, 0.25)' : 'transparent',
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
                {sanitizeText(tag.name)}
                {onRemove && (
                    <button
                        className="tag-pill__remove"
                        onClick={handleRemove}
                        type="button"
                        aria-label={`Remove ${sanitizeText(tag.name)} tag`}
                    >
                        <X size={14} />
                    </button>
                )}
            </span>
        );
    } else {
        // Generate pastel color for custom tags
        backgroundColor = getPastelColorFromString(tag.name);
        textColor = getContrastingTextColor(backgroundColor);
        
        const classes = [
            'tag-pill',
            clickable && 'tag-pill--clickable',
            selected && 'tag-pill--selected',
            onRemove && 'tag-pill--removable',
        ].filter(Boolean).join(' ');
        
        const style = {
            backgroundColor,
            color: textColor,
            borderColor: selected ? 'rgba(15, 23, 42, 0.25)' : 'transparent',
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
                {sanitizeText(tag.name)}
                {onRemove && (
                    <button
                        className="tag-pill__remove"
                        onClick={handleRemove}
                        type="button"
                        aria-label={`Remove ${sanitizeText(tag.name)} tag`}
                        style={{ color: textColor }}
                    >
                        <X size={14} />
                    </button>
                )}
            </span>
        );
    }
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
