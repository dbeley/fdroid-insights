$(document).ready(function() {
	//Only needed for the filename of export files.
	//Normally set in the title tag of your page.
	document.title='F-Droid Insights - Easily explore F-Droid apps with data from external sources';
  	var numbersType = $.fn.dataTable.absoluteOrderNumber( [
    	{ value: 'N/A', position: 'bottom' }
  	] );

	// DataTable initialisation
	$('#insights').DataTable(
		{
			"dom": 'BlfrtipQ',
			"buttons": [
				'copy',
        		'csv',
				'excel',
				'print',
				'colvis'
			],
			"paging": true,
			"autoWidth": true,
			"aLengthMenu": [[10, 25, 50, 100, 1000, -1], [10, 25, 50, 100, 1000, "All"]],
			"pageLength": 25,
            "scrollToTop": true,
			"order": [[8, 'desc']],
    		"columnDefs": [
      	  	  { type: numbersType, targets: [2, 3] },
      	  	  { targets: [7, 8], render: DataTable.render.datetime('x', 'YYYY-MM-DD', 'en') },
      	      { width: "20%", targets: 0 },
    		],
    		"responsive": true
		}
	);
});
