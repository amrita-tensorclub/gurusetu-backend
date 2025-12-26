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