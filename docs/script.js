$(document).ready(function() {
	//Only needed for the filename of export files.
	//Normally set in the title tag of your page.
	document.title='F-Droid Insights - Explore F-Droid apps easily with data from external sources';
	$.fn.dataTable.moment( 'x' );
  	var numbersType = $.fn.dataTable.absoluteOrderNumber( [
    	{ value: 'N/A', position: 'bottom' }
  	] );

	// DataTable initialisation
	$('#insights').DataTable(
		{
			// "dom": '<Q"dt-buttons"Bf><"clear">lirtp',
			"dom": 'BQlfrtip',
			"buttons": [
				'copy',
        		'csv',
				'excel',
				'print',
				'colvis'
			],
			"paging": true,
			"autoWidth": true,
			"pageLength": 25,
			"order": [[2, 'desc']],
    		"columnDefs": [
      	  	  { type: numbersType, targets: [2, 3, 4, 5] }
    		],
    		// "searchBuilder": {
    		// 	preDefined: {
    		// 		criteria: [
    		// 			{
    		// 				data: "Categories",
    		// 				condition: "contains",
    		// 				value: ["Development"]
    		// 			}
    		// 		]
    		// 	}
    		// }
		}
	);
});
