import { useState, useEffect, useCallback } from "react";

export default function GalleryModal({ photos, initialIndex = 0, onClose }) {
    const [currentIndex, setCurrentIndex] = useState(initialIndex);

    useEffect(() => {
        setCurrentIndex(initialIndex);
    }, [initialIndex]);

    const handlePrevious = useCallback((e) => {
        if (e) e.stopPropagation();
        setCurrentIndex((prev) => (prev > 0 ? prev - 1 : photos.length - 1));
    }, [photos.length]);

    const handleNext = useCallback((e) => {
        if (e) e.stopPropagation();
        setCurrentIndex((prev) => (prev < photos.length - 1 ? prev + 1 : 0));
    }, [photos.length]);

    useEffect(() => {
        // Handle keyboard navigation
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onClose();
            } else if (e.key === 'ArrowLeft') {
                handlePrevious(e);
            } else if (e.key === 'ArrowRight') {
                handleNext(e);
            }
        };

        // Prevent body scroll when modal is open
        document.body.style.overflow = 'hidden';

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'unset';
        };
    }, [onClose, handlePrevious, handleNext]);

    const handleBackdropClick = (e) => {
        // Close if clicking on backdrop (not on image or controls)
        if (e.target === e.currentTarget || e.target.classList.contains('gallery-modal-backdrop')) {
            onClose();
        }
    };

    return (
        <div className="gallery-modal-backdrop" onClick={handleBackdropClick}>
            <div className="gallery-modal-container">
                <button
                    className="gallery-modal-close"
                    onClick={onClose}
                    aria-label="Close gallery"
                >
                    ×
                </button>

                {photos.length > 1 && (
                    <>
                        <button
                            className="gallery-modal-nav gallery-modal-prev"
                            onClick={handlePrevious}
                            aria-label="Previous photo"
                        >
                            ‹
                        </button>
                        <button
                            className="gallery-modal-nav gallery-modal-next"
                            onClick={handleNext}
                            aria-label="Next photo"
                        >
                            ›
                        </button>
                    </>
                )}

                <div className="gallery-modal-content">
                    <img
                        src={photos[currentIndex]}
                        alt={`Photo ${currentIndex + 1} of ${photos.length}`}
                        className="gallery-modal-image"
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>

                {photos.length > 1 && (
                    <div className="gallery-modal-indicator">
                        {currentIndex + 1} / {photos.length}
                    </div>
                )}
            </div>
        </div>
    );
}
