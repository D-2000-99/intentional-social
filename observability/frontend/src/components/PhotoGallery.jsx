import { useState } from "react";
import GalleryModal from "./GalleryModal";

export default function PhotoGallery({ photos }) {
    const [isGalleryOpen, setIsGalleryOpen] = useState(false);
    const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(0);

    if (!photos || photos.length === 0) return null;

    const handlePhotoClick = (index) => {
        setSelectedPhotoIndex(index);
        setIsGalleryOpen(true);
    };

    const handleCloseGallery = () => {
        setIsGalleryOpen(false);
    };

    // Single photo - full width
    if (photos.length === 1) {
        return (
            <>
                <div className="photo-gallery photo-gallery-single">
                    <img
                        src={photos[0]}
                        alt="Post photo 1"
                        className="photo-gallery-image"
                        onClick={() => handlePhotoClick(0)}
                        loading="lazy"
                        onError={(e) => {
                            console.error(`Failed to load image`);
                            e.target.style.display = 'none';
                        }}
                    />
                </div>
                {isGalleryOpen && (
                    <GalleryModal
                        photos={photos}
                        initialIndex={selectedPhotoIndex}
                        onClose={handleCloseGallery}
                    />
                )}
            </>
        );
    }

    // Two photos - side by side
    if (photos.length === 2) {
        return (
            <>
                <div className="photo-gallery photo-gallery-two">
                    <img
                        src={photos[0]}
                        alt="Post photo 1"
                        className="photo-gallery-image"
                        onClick={() => handlePhotoClick(0)}
                        loading="lazy"
                        onError={(e) => {
                            console.error(`Failed to load image`);
                            e.target.style.display = 'none';
                        }}
                    />
                    <img
                        src={photos[1]}
                        alt="Post photo 2"
                        className="photo-gallery-image"
                        onClick={() => handlePhotoClick(1)}
                        loading="lazy"
                        onError={(e) => {
                            console.error(`Failed to load image`);
                            e.target.style.display = 'none';
                        }}
                    />
                </div>
                {isGalleryOpen && (
                    <GalleryModal
                        photos={photos}
                        initialIndex={selectedPhotoIndex}
                        onClose={handleCloseGallery}
                    />
                )}
            </>
        );
    }

    // Three or more photos - space-saving layout
    // Large photo on left (2/3), two small photos stacked on right (1/3 each)
    const mainPhoto = photos[0];
    const rightPhotos = photos.slice(1, 3);
    const remainingCount = photos.length - 3;

    return (
        <>
            <div className="photo-gallery photo-gallery-multiple">
                <div className="photo-gallery-main" onClick={() => handlePhotoClick(0)}>
                    <img
                        src={mainPhoto}
                        alt="Post photo 1"
                        className="photo-gallery-image"
                        loading="lazy"
                        onError={(e) => {
                            console.error(`Failed to load image`);
                            e.target.style.display = 'none';
                        }}
                    />
                </div>
                <div className="photo-gallery-side">
                    {rightPhotos.map((photo, index) => (
                        <div
                            key={index + 1}
                            className="photo-gallery-side-item"
                            onClick={() => handlePhotoClick(index + 1)}
                        >
                            <img
                                src={photo}
                                alt={`Post photo ${index + 2}`}
                                className="photo-gallery-image"
                                loading="lazy"
                                onError={(e) => {
                                    console.error(`Failed to load image`);
                                    e.target.style.display = 'none';
                                }}
                            />
                            {index === 1 && remainingCount > 0 && (
                                <div className="photo-gallery-overlay">
                                    +{remainingCount} more
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
            {isGalleryOpen && (
                <GalleryModal
                    photos={photos}
                    initialIndex={selectedPhotoIndex}
                    onClose={handleCloseGallery}
                />
            )}
        </>
    );
}

