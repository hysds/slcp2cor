dir=/u/hm/NCal_Fire/proc/S1-SLCP_RM_M1S3_TN035_20170928T020704-20171022T020756_s2-resorb-ab71-v1.1.3-urgent_response

i=2   # subswath (1, 2, or 3)

dirm=${dir}/master/IW${i}        # master directory
dirg=${dir}/geom_master/IW${i}   # master geometry directory
dirs=${dir}/fine_coreg/IW${i}    # slave directory

mkdir s${i}
cd s${i}

mkdir cor_20170928_20171022
cd cor_20170928_20171022
slcp2cor.py -mdir ${dirm} -sdir ${dirs} -gdir ${dirg} -rlks 7 -alks 3 -ssize 1.0
cd ..
cd ..

