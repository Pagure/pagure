$(document).ready(function() {
  const MSG = 'Turn off preview and clear the input field to use a different quick reply.';

  let in_preview = false;
  function update_button() {
    const has_text = $("#comment").val() !== "";
    $('.qr-btn').toggleClass('disabled', in_preview || has_text);
    if (in_preview || has_text) {
      $('.qr').attr('data-original-title', MSG);
    } else {
      $('.qr').attr('data-original-title', '');
    }
  }

  $('.qr-reply').on('click', function (e) {
    let tgt = $('#comment');
    if (!tgt.val()) {
      tgt.val($(this).attr('data-qr')).focus();
    }
    $('.qr .dropdown-toggle').dropdown('toggle');
    update_button();
    return false;
  });
  // Disable selecting replies when in preview mode.
  $('#previewinmarkdown').on('click', function () {
    in_preview = !in_preview;
    update_button();
  });
  $('#editinmarkdown').on('click', function () {
    in_preview = !in_preview;
    update_button();
  });
  $('#comment').on('input propertychange', update_button);
  $('[data-toggle="tooltip"]').tooltip();
  update_button();
});
