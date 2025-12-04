// Main JavaScript for FBM Sports Center

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    $('.alert').each(function() {
        var alert = $(this);
        setTimeout(function() {
            alert.fadeOut('slow');
        }, 5000);
    });

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if( target.length ) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 100
            }, 1000);
        }
    });
    $(window).scroll(function() {
        if ($(window).scrollTop() > 50) {
            $('.navbar').addClass('scrolled');
        } else {
            $('.navbar').removeClass('scrolled');
        }
    });
    // Add fade-in animation to cards
    $('.card, .field-card').addClass('fade-in-up');

    // Enhanced form validation
    $('form').on('submit', function(e) {
        var form = $(this);
        var submitBtn = form.find('button[type="submit"]');
        
        // Add loading state to submit button
        submitBtn.addClass('loading').prop('disabled', true);
        
        // Remove loading state after 3 seconds (fallback)
        setTimeout(function() {
            submitBtn.removeClass('loading').prop('disabled', false);
        }, 3000);
    });

    // Click to open layout / campus images in modal
    $(document).on('click', '.js-layout-image', function (e) {
        e.preventDefault();
        var src = $(this).data('image-src') || this.src;
        if (!src) {
            return;
        }
        openImageModal(src);
    });

    // Close modal on ESC key
    $(document).on('keydown', function (e) {
        if (e.key === 'Escape') {
            closeImageModal();
        }
    });
});

// Field booking functions
function selectTimeSlot(element, timeSlotId, price) {
    // Remove selection from all time slots
    $('.time-slot-card').removeClass('selected');
    
    // Add selection to clicked time slot
    $(element).addClass('selected');
    
    // Update hidden form fields
    $('#selected-time-slot').val(timeSlotId);
    $('#booking-price').text(formatCurrency(price));
    
    // Show booking form
    $('#booking-form-section').slideDown();
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND'
    }).format(amount);
}

// Update field availability when date changes
function updateFieldAvailability(fieldId) {
    var selectedDate = $('#booking-date').val();
    if (!selectedDate) return;
    
    // Show loading state
    $('#time-slots-container').html('<div class="text-center p-4"><div class="spinner-border" role="status"></div></div>');
    
    $.ajax({
        url: `/fields/${fieldId}/availability/`,
        data: { date: selectedDate },
        success: function(response) {
            renderTimeSlots(response.time_slots);
        },
        error: function() {
            $('#time-slots-container').html('<div class="alert alert-danger">Có lỗi xảy ra khi tải thông tin khung giờ.</div>');
        }
    });
}

function renderTimeSlots(timeSlots) {
    var container = $('#time-slots-container');
    container.empty();
    
    if (timeSlots.length === 0) {
        container.html('<div class="alert alert-info">Không có khung giờ nào khả dụng.</div>');
        return;
    }
    
    var html = '<div class="time-slot-grid">';
    timeSlots.forEach(function(slot) {
        var cardClass = 'time-slot-card';
        var clickable = '';
        var statusIcon = '';
        var statusText = '';
        
        if (slot.is_past) {
            cardClass += ' past';
            statusIcon = '<i class="bi bi-clock-history text-muted"></i>';
            statusText = '<small class="text-muted">Đã qua</small>';
        } else if (slot.is_booked) {
            cardClass += ' booked';
            statusIcon = '<i class="bi bi-x-circle text-danger"></i>';
            statusText = '<small class="text-muted">Đã đặt</small>';
        } else if (slot.is_available) {
            cardClass += ' available';
            clickable = `onclick="selectTimeSlot(this, ${slot.id}, ${slot.price})"`;
            statusIcon = '<i class="bi bi-check-circle text-success"></i>';
        }
        
        html += `
            <div class="${cardClass}" ${clickable}>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${slot.name}</strong>
                    ${statusIcon}
                </div>
                <div class="text-muted mb-2">
                    ${slot.start_time} - ${slot.end_time}
                </div>
                <div class="fw-bold text-primary">
                    ${slot.price_formatted}
                </div>
                ${statusText ? `<div class="mt-2">${statusText}</div>` : ''}
            </div>
        `;
    });
    html += '</div>';
    
    container.html(html);
}

// Booking management functions
function confirmBooking(bookingId) {
    if (!confirm('Bạn có chắc chắn muốn xác nhận đơn đặt sân này?')) {
        return;
    }
    
    updateBookingStatus(bookingId, 'confirm', 'Xác nhận đơn đặt sân');
}

function startBooking(bookingId) {
    if (!confirm('Bắt đầu sử dụng sân?')) {
        return;
    }
    
    updateBookingStatus(bookingId, 'start', 'Bắt đầu sử dụng sân');
}

function completeBooking(bookingId) {
    if (!confirm('Đánh dấu hoàn thành sử dụng sân?')) {
        return;
    }
    
    updateBookingStatus(bookingId, 'complete', 'Hoàn thành sử dụng sân');
}

function cancelBooking(bookingId) {
    var reason = prompt('Nhập lý do hủy đơn đặt sân:');
    if (!reason) {
        return;
    }
    
    $.ajax({
        url: `/bookings/${bookingId}/cancel/`,
        method: 'POST',
        data: {
            'reason': reason,
            'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                showAlert('success', response.message);
                location.reload();
            } else {
                showAlert('danger', response.message);
            }
        },
        error: function() {
            showAlert('danger', 'Có lỗi xảy ra khi hủy đơn đặt sân.');
        }
    });
}

function updateBookingStatus(bookingId, action, actionName) {
    var button = $(`button[onclick*="${action}Booking(${bookingId})"]`);
    var originalText = button.text();
    
    // Add loading state
    button.addClass('loading').prop('disabled', true);
    
    $.ajax({
        url: `/bookings/${bookingId}/${action}/`,
        method: 'POST',
        data: {
            'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                showAlert('success', response.message);
                location.reload();
            } else {
                showAlert('danger', response.message);
            }
        },
        error: function() {
            showAlert('danger', `Có lỗi xảy ra khi ${actionName.toLowerCase()}.`);
        },
        complete: function() {
            button.removeClass('loading').prop('disabled', false);
        }
    });
}

// User management functions
function toggleUserActive(userId) {
    $.ajax({
        url: `/accounts/users/${userId}/toggle-active/`,
        method: 'POST',
        data: {
            'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                showAlert('success', response.message);
                
                // Update button text and class
                var button = $(`button[onclick="toggleUserActive(${userId})"]`);
                if (response.is_active) {
                    button.removeClass('btn-success').addClass('btn-warning')
                          .html('<i class="bi bi-person-x me-1"></i>Vô hiệu hóa');
                } else {
                    button.removeClass('btn-warning').addClass('btn-success')
                          .html('<i class="bi bi-person-check me-1"></i>Kích hoạt');
                }
            } else {
                showAlert('danger', response.message);
            }
        },
        error: function() {
            showAlert('danger', 'Có lỗi xảy ra khi cập nhật trạng thái người dùng.');
        }
    });
}

// Utility functions
function showAlert(type, message) {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts
    $('.alert').remove();
    
    // Add new alert to top of main content
    $('.main-content .container:first').prepend(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('success', 'Đã sao chép vào clipboard!');
    });
}

// Form validation helpers
function validatePhone(phone) {
    var phoneRegex = /^[0-9+\-\s()]+$/;
    return phoneRegex.test(phone) && phone.length >= 10;
}

function validateEmail(email) {
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Real-time search
function setupRealTimeSearch(inputSelector, resultsSelector) {
    var searchTimeout;
    
    $(inputSelector).on('input', function() {
        var query = $(this).val();
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function() {
            if (query.length >= 2) {
                performSearch(query, resultsSelector);
            } else {
                $(resultsSelector).empty();
            }
        }, 300);
    });
}

function performSearch(query, resultsSelector) {
    // This would be implemented based on specific search requirements
    console.log('Searching for:', query);
}

// Image preview for file uploads
function previewImage(input, previewSelector) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        
        reader.onload = function(e) {
            $(previewSelector).attr('src', e.target.result).show();
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}

// Date picker initialization
function initializeDatePickers() {
    // Set minimum date to today for booking dates
    var today = new Date().toISOString().split('T')[0];
    $('input[type="date"]').attr('min', today);
}

// Image modal & zoom for campus map / layouts
let currentZoom = 1;

function openImageModal(src) {
    if (!src) {
        return;
    }
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('image-modal-img');
    currentZoom = 1;
    img.src = src;
    img.style.transform = 'scale(1)';
    modal.style.display = 'block';
    // Lock background scroll
    document.body.style.overflow = 'hidden';
}

function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.style.display = 'none';
    // Restore background scroll
    document.body.style.overflow = '';
}

function zoomImage(delta) {
    const img = document.getElementById('image-modal-img');
    currentZoom = Math.min(Math.max(currentZoom + delta, 0.5), 3);
    img.style.transform = `scale(${currentZoom})`;
}

function resetZoom() {
    const img = document.getElementById('image-modal-img');
    currentZoom = 1;
    img.style.transform = 'scale(1)';
}

// Initialize on page load
$(document).ready(function() {
    initializeDatePickers();

    // Real-time search setup
    if ($('#search-input').length) {
        setupRealTimeSearch('#search-input', '#search-results');
    }

    // Image preview setup
    $('input[type="file"][accept*="image"]').change(function() {
        var previewId = $(this).data('preview');
        if (previewId) {
            previewImage(this, '#' + previewId);
        }
    });

    // Auto-resize textareas based on content
    $('textarea.form-control').each(function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    }).on('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});
