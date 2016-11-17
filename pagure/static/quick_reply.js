$(document).ready(function() {
  $('.qr-reply').on('click', function (e) {
    let tgt = $('#comment');
    if (!tgt.val()) {
      tgt.val($(this).attr('data-qr'));
    }
    $('.qr .dropdown-toggle').dropdown('toggle');
    return false;
  });
  // Disable selecting replies when in preview mode.
  $('#previewinmarkdown').on('click', function () {
    $('.qr-btn').toggleClass('disabled');
  });
});
