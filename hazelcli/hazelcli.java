/*
 * Hazelcast client for commandline invoking purpose
 *
 * by Samuel Chen
 */

import com.hazelcast.core.HazelcastInstance;
import com.hazelcast.client.HazelcastClient;
import com.hazelcast.client.config.ClientConfig;

import java.util.Map;
import java.util.Collection;

import com.gagein.cache.model.mem.MemberPreferenceKey;
import com.emm.db.util.RowMap;

public class hazelcli {

	public static void main(String args[]) {
	    Boolean succeed = false;

		String servers = "192.168.1.90:7701";
		String user = "dev";
		String password = "dev-pass";
		String map_name = "app.mem.MemberPreference";
        //String key = "-10__101__Monitor.DB.CheckPoint";
		String memid = "-10";
		String group = "101";
		String keystr = "Monitor.DB.CheckPoint";

		if (args.length > 0) {
		    servers = args[0];
		    log(String.format("cluster servers: %s", servers));
		}

		MemberPreferenceKey key = new MemberPreferenceKey(memid, group, keystr);
		//MemberPreferenceKey key = new MemberPreferenceKey("-10", "101", "SolrIndex.member");

		ClientConfig clientConfig = new ClientConfig();
		clientConfig.getGroupConfig().setName(user).setPassword(password);
		clientConfig.addAddress(servers.split(","));

		HazelcastInstance client = null;

		try {
            client = HazelcastClient.newHazelcastClient(clientConfig);

            // check values
            Map<String, Object> map = client.getMap(map_name);
            RowMap value = (RowMap)map.get(key);
            if (null != value && value.size() > 0) {
                String result = (String)value.get("pref_value");
                log(String.format("Got result: %s", result));
                report(String.format("Found %d record with result %s ", value.size(), result));
            } else {
                log("No result found");
                report("Found 0 record.");
            }


            // -10__101__SolrIndex.member - {pref_memid=-10, pref_group=101, pref_date=Thu Jul 03 16:16:30 CST 2014, pref_value=2014-06-23 21:02:34, pref_key=SolrIndex.member}

            /*
            System.out.println(">>>>> ALL");
            for (Map.Entry<String, Object> entry: value.entrySet()){
                Object k = entry.getKey();
                Object v = entry.getValue();
                System.out.print(k);
                System.out.print(" - ");
                System.out.println(v);
            }
            */

            succeed = true;

        } catch (Exception ex) {
            log(">> Exception : ");
            log(ex.toString());
            report("Exception:");
            report(ex.toString());
        } finally {
            if (null !=client) client.shutdown();
        }

        if (succeed) {
            report("SUCCEED");
        } else {
            report("FAIL");
        }


    }

    private static void log(String text) {
        System.err.println(text);
    }

    private static void report(String text) {
        System.out.println(text);
    }
}

