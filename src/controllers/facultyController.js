const supabase = require('../config/supabase');

exports.getAllFaculty = async (req, res) => {
    try {
        console.log("Fetching Faculty...");
        const { data: faculty, error: facultyError } = await supabase
            .from('faculty')
            .select('*');
        if (facultyError) throw facultyError;

        const { data: mappings, error: mappingError } = await supabase
            .from('cabin_mappings')
            .select('*');
        
        // Manual Join
        const joinedData = faculty.map(prof => {
            const mapData = mappings ? mappings.find(m => m.cabin_code === prof.cabin_number) : null;
            return { ...prof, cabin_mappings: mapData || null };
        });

        res.status(200).json(joinedData);

    } catch (err) {
        console.error('Controller Error:', err.message);
        res.status(500).json({ error: err.message });
    }
};

//REQUEST UPDATE (Spam Protection)
exports.requestUpdate = async (req, res) => {
    const { id } = req.params;
    try {
        const { data: faculty, error } = await supabase
            .from('faculty')
            .select('request_count, name').eq('id', id).single();
        
        if (error) throw error;

        let newCount = (faculty.request_count || 0) + 1;
        if (newCount >= 3) {
            console.log(`🚨 NOTIFICATION SENT TO ${faculty.name}`);
            newCount = 0; 
        }

        await supabase.from('faculty').update({ request_count: newCount }).eq('id', id);
        res.status(200).json({ message: "Request counted", count: newCount });

    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};

//  UPDATE STATUS 
exports.updateStatus = async (req, res) => {
    const { id } = req.params;
    const { status, source } = req.body;

    try {
        const { data, error } = await supabase
            .from('faculty')
            .update({ 
                current_status: status,
                status_source: source,
                last_status_updated: new Date()
            })
            .eq('id', id)
            .select();

        if (error) throw error;
        res.status(200).json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};
// 4. CHECK FUTURE AVAILABILITY
exports.checkFutureAvailability = async (req, res) => {
    const { id } = req.params; // Faculty ID
    const { datetime } = req.body; // e.g. "2023-12-25T10:00"

    try {
        const dateObj = new Date(datetime);
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const dayOfWeek = days[dateObj.getDay()];
        
        // Format time as HH:MM:00 for SQL comparison
        const timeStr = dateObj.toTimeString().split(' ')[0]; 

        // Query the Timetable Table
        const { data, error } = await supabase
            .from('timetables')
            .select('*')
            .eq('faculty_id', id)
            .eq('day_of_week', dayOfWeek)
            .lte('start_time', timeStr) // Class started before or at this time
            .gte('end_time', timeStr);  // And ends after this time

        if (error) throw error;

        if (data && data.length > 0) {
            // Found a class!
            res.status(200).json({ 
                status: 'Busy', 
                activity: data[0].activity,
                message: `In ${data[0].activity} (${data[0].start_time} - ${data[0].end_time})`
            });
        } else {
            // No class found
            res.status(200).json({ 
                status: 'Available', 
                message: 'Free according to timetable' 
            });
        }

    } catch (err) {
        console.error("Future Check Error:", err);
        res.status(500).json({ error: err.message });
    }
};